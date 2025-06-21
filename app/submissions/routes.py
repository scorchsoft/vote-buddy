from flask import render_template, redirect, url_for, flash, abort
from ..extensions import db
from ..models import Meeting, Motion, MotionSubmission, AmendmentSubmission
from ..services.email import (
    send_motion_submission_alert,
    send_amendment_submission_alert,
)
from . import bp
from .forms import MotionSubmissionForm, AmendmentSubmissionForm


@bp.route('/motion/<int:meeting_id>', methods=['GET', 'POST'])
def submit_motion(meeting_id: int):
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None:
        abort(404)
    form = MotionSubmissionForm()
    if form.validate_on_submit():
        sub = MotionSubmission(
            meeting_id=meeting.id,
            name=form.name.data,
            email=form.email.data,
            title=form.title.data,
            text_md=form.text_md.data,
        )
        db.session.add(sub)
        db.session.commit()
        send_motion_submission_alert(sub, meeting)
        flash('Motion submitted for review', 'success')
        return redirect(url_for('main.public_meeting_detail', meeting_id=meeting.id))
    return render_template('submissions/motion_form.html', form=form, meeting=meeting)


@bp.route('/amendment/<int:motion_id>', methods=['GET', 'POST'])
def submit_amendment(motion_id: int):
    motion = db.session.get(Motion, motion_id)
    if motion is None:
        abort(404)
    meeting = db.session.get(Meeting, motion.meeting_id)
    form = AmendmentSubmissionForm()
    if form.validate_on_submit():
        sub = AmendmentSubmission(
            motion_id=motion.id,
            name=form.name.data,
            email=form.email.data,
            text_md=form.text_md.data,
        )
        db.session.add(sub)
        db.session.commit()
        send_amendment_submission_alert(sub, motion, meeting)
        flash('Amendment submitted for review', 'success')
        return redirect(url_for('meetings.view_motion', motion_id=motion.id))
    return render_template('submissions/amendment_form.html', form=form, motion=motion)
