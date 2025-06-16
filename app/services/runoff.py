from datetime import timedelta
from uuid6 import uuid7
from flask import current_app
import json
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
        'TIE_BREAK_DECISIONS', {}, parser=lambda v: json.loads(v) if isinstance(v, str) else v
    )
    for amend in amendments:
        for_count = Vote.query.filter_by(amendment_id=amend.id, choice='for').count()
        against_count = Vote.query.filter_by(amendment_id=amend.id, choice='against').count()
        if for_count > against_count:
            amend.status = 'carried'
        elif for_count < against_count:
            amend.status = 'failed'
        else:
            decision = decisions.get(amend.id)
            if decision:
                amend.status = decision['result']
                amend.tie_break_method = decision['method']
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
        meeting.opens_at_stage2 = (meeting.opens_at_stage2 or meeting.closes_at_stage1) + extension
        meeting.closes_at_stage2 = (meeting.closes_at_stage2 or meeting.opens_at_stage2) + extension
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
        a = Amendment.query.get(conflict.amendment_a_id)
        b = Amendment.query.get(conflict.amendment_b_id)
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
