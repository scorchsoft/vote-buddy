from flask import render_template, redirect, url_for, flash, abort, current_app
from datetime import datetime
from ..extensions import db
from ..models import (
    Meeting,
    Motion,
    Member,
    MotionSubmission,
    AmendmentSubmission,
    SubmissionToken,
)
from ..services.email import (
    send_motion_submission_alert,
    send_amendment_submission_alert,
    notify_seconder_motion,
    notify_seconder_amendment,
)
from . import bp
from .forms import MotionSubmissionForm, AmendmentSubmissionForm


@bp.route('/<token>/motion/<int:meeting_id>', methods=['GET', 'POST'])
def submit_motion(token: str, meeting_id: int):
    token_obj = SubmissionToken.verify(token, current_app.config["TOKEN_SALT"])
    if not token_obj or token_obj.meeting_id != meeting_id:
        abort(404)
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None:
        abort(404)
    member = db.session.get(Member, token_obj.member_id)
    if member is None or member.meeting_id != meeting_id:
        abort(404)
    form = MotionSubmissionForm(name=member.name, email=member.email)
    members = Member.query.filter_by(meeting_id=meeting.id).order_by(Member.name).all()
    form.seconder_id.choices = [(m.id, m.name) for m in members if m.id != member.id]
    if form.validate_on_submit():
        sub = MotionSubmission(
            meeting_id=meeting.id,
            member_id=member.id,
            name=form.name.data,
            email=form.email.data,
            seconder_id=form.seconder_id.data,
            title=form.title.data,
            text_md=form.text_md.data,
        )
        db.session.add(sub)
        token_obj.used_at = datetime.utcnow()
        db.session.commit()
        send_motion_submission_alert(sub, meeting)
        seconder = db.session.get(Member, form.seconder_id.data)
        if seconder:
            notify_seconder_motion(seconder, meeting)
        flash('Motion submitted for review', 'success')
        return redirect(url_for('main.public_meeting_detail', meeting_id=meeting.id))
    return render_template('submissions/motion_form.html', form=form, meeting=meeting)


@bp.route('/<token>/amendment/<int:motion_id>', methods=['GET', 'POST'])
def submit_amendment(token: str, motion_id: int):
    motion = db.session.get(Motion, motion_id)
    if motion is None:
        abort(404)
    token_obj = SubmissionToken.verify(token, current_app.config["TOKEN_SALT"])
    if not token_obj or token_obj.meeting_id != motion.meeting_id:
        abort(404)
    meeting = db.session.get(Meeting, motion.meeting_id)
    member = db.session.get(Member, token_obj.member_id)
    if member is None or member.meeting_id != meeting.id:
        abort(404)
    form = AmendmentSubmissionForm(name=member.name, email=member.email)
    members = Member.query.filter_by(meeting_id=meeting.id).order_by(Member.name).all()
    form.seconder_id.choices = [(m.id, m.name) for m in members if m.id != member.id]
    if form.validate_on_submit():
        sub = AmendmentSubmission(
            motion_id=motion.id,
            member_id=member.id,
            name=form.name.data,
            email=form.email.data,
            seconder_id=form.seconder_id.data,
            text_md=form.text_md.data,
        )
        db.session.add(sub)
        token_obj.used_at = datetime.utcnow()
        db.session.commit()
        send_amendment_submission_alert(sub, motion, meeting)
        seconder = db.session.get(Member, form.seconder_id.data)
        if seconder:
            notify_seconder_amendment(seconder, meeting, motion)
        flash('Amendment submitted for review', 'success')
        return redirect(url_for('meetings.view_motion', motion_id=motion.id))
    return render_template('submissions/amendment_form.html', form=form, motion=motion)
