from datetime import datetime, timedelta
import json
from flask import current_app
from ..utils import config_or_setting

from ..extensions import db
from ..models import (
    Amendment,
    AmendmentConflict,
    Member,
    Meeting,
    Runoff,
    Vote,
    VoteToken,
)


def close_stage1(meeting: Meeting) -> tuple[list[Runoff], list[tuple[Member, str]]]:
    """Finalize Stage 1 results and create run-off ballots if needed."""
    amendments = (
        Amendment.query.filter_by(meeting_id=meeting.id)
        .order_by(Amendment.order)
        .all()
    )
    tie_map: dict[int, list[Amendment]] = {}
    decisions = config_or_setting(
        'TIE_BREAK_DECISIONS',
        {},
        parser=lambda v: json.loads(v) if isinstance(v, str) else v,
    )
    for amend in amendments:
        for_count = Vote.query.filter_by(amendment_id=amend.id, choice='for').count()
        against_count = Vote.query.filter_by(amendment_id=amend.id, choice='against').count()
        if for_count > against_count:
            amend.status = 'carried'
            amend.tie_break_method = None
        elif for_count < against_count:
            amend.status = 'failed'
            amend.tie_break_method = None
        else:
            decision = decisions.get(str(amend.id)) or decisions.get(amend.id)
            if decision:
                amend.status = decision.get('result')
                amend.tie_break_method = decision.get('method')
            elif amend.tie_break_method:
                # decision entered by Returning Officer
                pass
            else:
                amend.status = 'tied'
                tie_map.setdefault(amend.motion_id, []).append(amend)
    # resolve any remaining ties by amendment order
    for tied in tie_map.values():
        if len(tied) == 1:
            loser = tied[0]
            loser.status = 'failed'
            loser.tie_break_method = 'order'
            continue
        tied.sort(key=lambda a: a.order)
        winner = tied[0]
        winner.status = 'carried'
        winner.tie_break_method = 'order'
        for loser in tied[1:]:
            loser.status = 'failed'
            loser.tie_break_method = 'order'

    db.session.commit()

    runoffs = _detect_runoffs(meeting)
    tokens_to_send: list[tuple[Member, str]] = []
    if runoffs:
        extension = timedelta(
            minutes=config_or_setting('RUNOFF_EXTENSION_MINUTES', 2880, parser=int)
        )
        now = datetime.utcnow()
        meeting.runoff_opens_at = now
        meeting.runoff_closes_at = now + extension
        new_opens = (meeting.opens_at_stage2 or meeting.closes_at_stage1) + extension
        new_closes = (meeting.closes_at_stage2 or new_opens) + extension
        meeting.opens_at_stage2 = new_opens
        meeting.closes_at_stage2 = new_closes
        db.session.commit()
        members = Member.query.filter_by(meeting_id=meeting.id).all()
        for member in members:
            _, plain = VoteToken.create(
                member_id=member.id,
                stage=1,
                salt=current_app.config["TOKEN_SALT"],
            )
            tokens_to_send.append((member, plain))
        db.session.commit()
    return runoffs, tokens_to_send


def _detect_runoffs(meeting: Meeting) -> list[Runoff]:
    runoffs_created: list[Runoff] = []
    conflicts = AmendmentConflict.query.filter_by(meeting_id=meeting.id).all()
    for conflict in conflicts:
        a = db.session.get(Amendment, conflict.amendment_a_id)
        b = db.session.get(Amendment, conflict.amendment_b_id)
        if a.status == 'carried' and b.status == 'carried':
            if not Runoff.query.filter_by(
                meeting_id=meeting.id,
                amendment_a_id=a.id,
                amendment_b_id=b.id,
            ).first():
                runoff = Runoff(
                    meeting_id=meeting.id,
                    amendment_a_id=a.id,
                    amendment_b_id=b.id,
                )
                db.session.add(runoff)
                runoffs_created.append(runoff)
    db.session.commit()
    return runoffs_created


def close_runoff_stage(meeting: Meeting) -> None:
    """Tally run-off votes and finalise amendment statuses."""
    runoffs = Runoff.query.filter_by(meeting_id=meeting.id).all()
    for rof in runoffs:
        a = db.session.get(Amendment, rof.amendment_a_id)
        b = db.session.get(Amendment, rof.amendment_b_id)
        a_for = Vote.query.filter_by(amendment_id=a.id, choice="for").count()
        b_for = Vote.query.filter_by(amendment_id=b.id, choice="for").count()
        if a_for > b_for:
            winner, loser = a, b
        elif b_for > a_for:
            winner, loser = b, a
        else:
            winner, loser = (a, b) if a.order <= b.order else (b, a)
        winner.status = "carried"
        loser.status = "failed"

    tokens = (
        VoteToken.query.join(Member, VoteToken.member_id == Member.id)
        .filter(Member.meeting_id == meeting.id, VoteToken.stage == 1)
        .all()
    )
    for t in tokens:
        db.session.delete(t)

    db.session.commit()
