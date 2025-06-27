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
from ..permissions import permission_required
from flask_login import login_required, current_user


@bp.route('/<int:meeting_id>')
@login_required
@permission_required('manage_meetings')
def list_submissions(meeting_id: int):
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None:
        abort(404)
    motions = MotionSubmission.query.filter_by(meeting_id=meeting.id).all()
    amendments = (
        AmendmentSubmission.query.join(Motion, AmendmentSubmission.motion_id == Motion.id)
        .filter(Motion.meeting_id == meeting.id)
        .all()
    )
    return render_template('submissions/list.html', meeting=meeting, motions=motions, amendments=amendments)


@bp.post('/motion/<int:submission_id>/publish')
@login_required
@permission_required('manage_meetings')
def publish_motion(submission_id: int):
    sub = db.session.get(MotionSubmission, submission_id)
    if sub is None:
        abort(404)
    motion = Motion(
        meeting_id=sub.meeting_id,
        title=sub.title,
        text_md=sub.text_md,
        category='motion',
        threshold='normal',
        ordering=Motion.query.filter_by(meeting_id=sub.meeting_id).count() + 1,
        is_published=True,
    )
    db.session.add(motion)
    db.session.delete(sub)
    db.session.commit()
    flash('Motion published', 'success')
    return redirect(url_for('submissions.list_submissions', meeting_id=motion.meeting_id))


@bp.post('/amendment/<int:submission_id>/publish')
@login_required
@permission_required('manage_meetings')
def publish_amendment(submission_id: int):
    sub = db.session.get(AmendmentSubmission, submission_id)
    if sub is None:
        abort(404)
    motion = db.session.get(Motion, sub.motion_id)
    amend = Amendment(
        meeting_id=motion.meeting_id,
        motion_id=motion.id,
        text_md=sub.text_md,
        order=Amendment.query.filter_by(motion_id=motion.id).count() + 1,
        proposer_id=sub.member_id,
        seconder_id=sub.seconder_id,
        is_published=True,
    )
    db.session.add(amend)
    db.session.delete(sub)
    db.session.commit()
    flash('Amendment published', 'success')
    return redirect(url_for('submissions.list_submissions', meeting_id=motion.meeting_id))


@bp.post('/motion/<int:submission_id>/reject')
@login_required
@permission_required('manage_meetings')
def reject_motion(submission_id: int):
    sub = db.session.get(MotionSubmission, submission_id)
    if sub is None:
        abort(404)
    meeting_id = sub.meeting_id
    db.session.delete(sub)
    db.session.commit()
    flash('Motion rejected', 'success')
    return redirect(url_for('submissions.list_submissions', meeting_id=meeting_id))


@bp.post('/amendment/<int:submission_id>/reject')
@login_required
@permission_required('manage_meetings')
def reject_amendment(submission_id: int):
    sub = db.session.get(AmendmentSubmission, submission_id)
    if sub is None:
        abort(404)
    motion = db.session.get(Motion, sub.motion_id)
    meeting_id = motion.meeting_id if motion else None
    db.session.delete(sub)
    db.session.commit()
    flash('Amendment rejected', 'success')
    return redirect(url_for('submissions.list_submissions', meeting_id=meeting_id))


@bp.route('/<token>/motion/<int:meeting_id>', methods=['GET', 'POST'])
def submit_motion(token: str, meeting_id: int):
    if token == "preview":
        token_obj = type("Tok", (), {
            "member_id": Member.query.filter_by(meeting_id=meeting_id).first().id if Member.query.filter_by(meeting_id=meeting_id).first() else None,
            "meeting_id": meeting_id,
        })
    else:
        token_obj = SubmissionToken.verify(token, current_app.config["TOKEN_SALT"])
        if not token_obj or token_obj.meeting_id != meeting_id:
            abort(404)
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None:
        abort(404)
    now = datetime.utcnow()
    if meeting.motions_opens_at and now < meeting.motions_opens_at:
        flash('Motion submissions have not opened yet.', 'error')
        return redirect(url_for('main.public_meeting_detail', meeting_id=meeting.id))
    if meeting.motions_closes_at and now > meeting.motions_closes_at:
        flash('Motion submission window has closed.', 'error')
        return redirect(url_for('main.public_meeting_detail', meeting_id=meeting.id))
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
        return render_template('submissions/motion_submitted.html', meeting=meeting, token=token)
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
    now = datetime.utcnow()
    if meeting.amendments_opens_at and now < meeting.amendments_opens_at:
        flash('Amendment submissions have not opened yet.', 'error')
        return redirect(url_for('meetings.view_motion', motion_id=motion.id))
    if meeting.amendments_closes_at and now > meeting.amendments_closes_at:
        flash('Amendment submission window has closed.', 'error')
        return redirect(url_for('meetings.view_motion', motion_id=motion.id))
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
    return render_template('submissions/amendment_form.html', form=form, motion=motion, meeting=meeting)
