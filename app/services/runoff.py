from datetime import timedelta
from uuid6 import uuid7
from flask import current_app

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


def close_stage1(meeting: Meeting) -> list[Runoff]:
    """Finalize Stage 1 results and create run-off ballots if needed."""
    amendments = Amendment.query.filter_by(meeting_id=meeting.id).all()
    for amend in amendments:
        for_count = Vote.query.filter_by(amendment_id=amend.id, choice='for').count()
        against_count = Vote.query.filter_by(amendment_id=amend.id, choice='against').count()
        amend.status = 'carried' if for_count > against_count else 'failed'
    db.session.commit()

    runoffs = _detect_runoffs(meeting)
    if runoffs:
        extension = timedelta(
            minutes=current_app.config.get('RUNOFF_EXTENSION_MINUTES', 2880)
        )
        meeting.opens_at_stage2 = (meeting.opens_at_stage2 or meeting.closes_at_stage1) + extension
        meeting.closes_at_stage2 = (meeting.closes_at_stage2 or meeting.opens_at_stage2) + extension
        db.session.commit()
        members = Member.query.filter_by(meeting_id=meeting.id).all()
        for member in members:
            token = VoteToken(token=str(uuid7()), member_id=member.id, stage=1)
            db.session.add(token)
        db.session.commit()
    return runoffs


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
