import os
from flask import (
    Blueprint,
    render_template,
    abort,
    jsonify,
    request,
    current_app,
    send_file,
    url_for,
    send_from_directory,
    Response,
)
from .extensions import db, limiter
from .models import (
    Meeting,
    Amendment,
    Motion,
    Vote,
    Member,
    VoteToken,
    Runoff,
    AppSetting,
    MeetingFile,
)
from .services.email import send_vote_invite, send_stage2_invite, send_runoff_invite
from .utils import generate_stage_ics, generate_runoff_ics, generate_results_pdf
from .voting.routes import compile_motion_text
import io
from sqlalchemy import func
from flask_login import login_required
from .permissions import permission_required

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    return render_template('index.html')


@bp.route('/results')
def results_index():
    """List meetings with public results."""
    meetings = (
        Meeting.query.filter_by(public_results=True)
        .order_by(Meeting.title)
        .all()
    )
    return render_template('results_index.html', meetings=meetings)


@bp.route('/public/meetings')
def public_meetings():
    """List meetings for public view."""
    meetings = Meeting.query.order_by(Meeting.title).all()
    member_counts = {
        m.id: Member.query.filter_by(meeting_id=m.id).count() for m in meetings
    }
    return render_template(
        'public_meetings.html', meetings=meetings, member_counts=member_counts
    )


@bp.route('/public/meetings/<int:meeting_id>')
def public_meeting_detail(meeting_id: int):
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None:
        abort(404)
    member_count = Member.query.filter_by(meeting_id=meeting.id).count()
    files = MeetingFile.query.filter_by(meeting_id=meeting.id).all()
    contact_url = AppSetting.get(
        'contact_url', 'https://www.britishpowerlifting.org/contactus'
    )
    stage1_ics_url = url_for('main.public_stage1_ics', meeting_id=meeting.id)
    stage2_ics_url = url_for('main.public_stage2_ics', meeting_id=meeting.id)
    runoff_ics_url = url_for('main.public_runoff_ics', meeting_id=meeting.id)
    return render_template(
        'public_meeting.html',
        meeting=meeting,
        member_count=member_count,
        contact_url=contact_url,
        stage1_ics_url=stage1_ics_url,
        runoff_ics_url=runoff_ics_url,
        stage2_ics_url=stage2_ics_url,
        files=files,
    )


def _resend_key_func():
    email = request.form.get("email", "").strip().lower()
    return email or request.remote_addr


@bp.post('/public/meetings/<int:meeting_id>/resend')
@limiter.limit('5 per hour', key_func=_resend_key_func)
def resend_meeting_link_public(meeting_id: int):
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None:
        abort(404)
    email = request.form.get('email', '').strip().lower()
    member_number = request.form.get('member_number', '').strip()

    current_app.logger.info(
        'Resend attempt for meeting=%s email=%s member=%s',
        meeting_id,
        email,
        member_number,
    )

    member = Member.query.filter_by(
        meeting_id=meeting.id, member_number=member_number, email=email
    ).first()
    if member:
        stage = 2 if meeting.status in {'Stage 2', 'Pending Stage 2'} else 1
        token_obj, plain = VoteToken.create(
            member_id=member.id, stage=stage, salt=current_app.config['TOKEN_SALT']
        )
        db.session.commit()
        if stage == 2:
            send_stage2_invite(member, plain, meeting)
        else:
            if Runoff.query.filter_by(meeting_id=meeting.id).count() > 0:
                send_runoff_invite(member, plain, meeting)
            else:
                send_vote_invite(member, plain, meeting)
        current_app.logger.info(
            'Resend email sent to %s for member %s', email, member_number
        )
    else:
        current_app.logger.info(
            'Resend attempted for unknown member: %s/%s', email, member_number
        )

    message = (
        'If the details are correct, a new voting link will be sent shortly.'
    )
    success = True
    contact_url = AppSetting.get(
        'contact_url', 'https://www.britishpowerlifting.org/contactus'
    )
    return render_template(
        'resend_modal_content.html',
        message=message,
        success=success,
        contact_url=contact_url,
    )


@bp.route('/public/meetings/<int:meeting_id>/stage1.ics')
def public_stage1_ics(meeting_id: int):
    """Download Stage 1 calendar file for the public."""
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None:
        abort(404)
    try:
        ics = generate_stage_ics(meeting, 1)
    except ValueError:
        abort(404)
    return send_file(
        io.BytesIO(ics),
        mimetype='text/calendar',
        as_attachment=True,
        download_name='stage1.ics',
    )


@bp.route('/public/meetings/<int:meeting_id>/stage2.ics')
def public_stage2_ics(meeting_id: int):
    """Download Stage 2 calendar file for the public."""
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None:
        abort(404)
    try:
        ics = generate_stage_ics(meeting, 2)
    except ValueError:
        abort(404)
    return send_file(
        io.BytesIO(ics),
        mimetype='text/calendar',
        as_attachment=True,
        download_name='stage2.ics',
    )


@bp.route('/public/meetings/<int:meeting_id>/runoff.ics')
def public_runoff_ics(meeting_id: int):
    """Download run-off calendar file if timestamps are set."""
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None:
        abort(404)
    try:
        ics = generate_runoff_ics(meeting)
    except ValueError:
        abort(404)
    return send_file(
        io.BytesIO(ics),
        mimetype='text/calendar',
        as_attachment=True,
        download_name='runoff.ics',
    )


@bp.route('/public/meetings/<int:meeting_id>/files/<int:file_id>')
def public_meeting_file(meeting_id: int, file_id: int):
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None:
        abort(404)
    file_rec = MeetingFile.query.filter_by(meeting_id=meeting.id, id=file_id).first()
    if file_rec is None:
        abort(404)
    root = current_app.config.get(
        'UPLOAD_FOLDER', os.path.join(current_app.instance_path, 'files')
    )
    meeting_dir = os.path.join(root, str(meeting.id))
    resp = send_from_directory(
        meeting_dir,
        file_rec.filename,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"{file_rec.title or 'file'}.pdf",
    )
    resp.headers["Content-Disposition"] = (
        f"attachment; filename=\"{file_rec.title or 'file'}.pdf\""
    )
    return resp


def _vote_counts(query):
    counts = {'for': 0, 'against': 0, 'abstain': 0}
    rows = (
        db.session.query(Vote.choice, func.count(Vote.id))
        .filter(query)
        .group_by(Vote.choice)
        .all()
    )
    for choice, count in rows:
        counts[choice] = count
    return counts


@bp.route('/results/<int:meeting_id>/stage1')
def public_stage1_results(meeting_id: int):
    """Show Stage 1 results when awaiting Stage 2."""
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None:
        abort(404)
    if meeting.status != 'Pending Stage 2' or not meeting.early_public_results:
        abort(404)

    amendments = (
        Amendment.query.filter_by(meeting_id=meeting.id)
        .order_by(Amendment.order)
        .all()
    )
    results = []
    for amend in amendments:
        results.append((amend, _vote_counts(Vote.amendment_id == amend.id)))

    return render_template('public_stage1_results.html', meeting=meeting, results=results)


@bp.route('/results/<int:meeting_id>')
def public_results(meeting_id: int):
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None:
        abort(404)
    if not meeting.public_results:
        abort(404)

    amendments = (
        Amendment.query.filter_by(meeting_id=meeting.id)
        .order_by(Amendment.order)
        .all()
    )
    stage1 = []
    for amend in amendments:
        stage1.append((amend, _vote_counts(Vote.amendment_id == amend.id)))

    motions = (
        Motion.query.filter_by(meeting_id=meeting.id)
        .order_by(Motion.ordering)
        .all()
    )
    stage2 = []
    for motion in motions:
        stage2.append((motion, _vote_counts(Vote.motion_id == motion.id)))

    return render_template(
        'public_results.html', meeting=meeting, stage1=stage1, stage2=stage2
    )


@bp.route('/results/<int:meeting_id>/charts')
def public_results_charts(meeting_id: int):
    meeting = db.session.get(Meeting, meeting_id)
    if not meeting:
        abort(404)
    if not meeting.public_results:
        abort(404)
    return render_template('results_chart.html', meeting=meeting)


@bp.route('/results/<int:meeting_id>/tallies.json')
def public_results_json(meeting_id: int):
    """Return tallies for amendments and motions as JSON."""
    meeting = db.session.get(Meeting, meeting_id)
    if not meeting:
        abort(404)
    if not meeting.public_results:
        abort(404)

    tallies: list[dict[str, int | str]] = []
    amendments = (
        Amendment.query.filter_by(meeting_id=meeting.id)
        .order_by(Amendment.order)
        .all()
    )
    for amend in amendments:
        counts = _vote_counts(Vote.amendment_id == amend.id)
        tallies.append(
            {
                "type": "amendment",
                "id": amend.id,
                "text": amend.text_md[:40],
                **counts,
            }
        )

    motions = (
        Motion.query.filter_by(meeting_id=meeting.id)
        .order_by(Motion.ordering)
        .all()
    )
    for motion in motions:
        counts = _vote_counts(Vote.motion_id == motion.id)
        tallies.append(
            {
                "type": "motion",
                "id": motion.id,
                "text": motion.title,
                **counts,
            }
        )

    return jsonify({"meeting_id": meeting.id, "tallies": tallies})


@bp.route('/results/<int:meeting_id>/final.pdf')
def public_results_pdf(meeting_id: int):
    """Download PDF summary of Stage 1 and Stage 2 results."""
    meeting = db.session.get(Meeting, meeting_id)
    if not meeting:
        abort(404)
    if not meeting.public_results:
        abort(404)

    amendments = (
        Amendment.query.filter_by(meeting_id=meeting.id)
        .order_by(Amendment.order)
        .all()
    )
    stage1 = [(a, _vote_counts(Vote.amendment_id == a.id)) for a in amendments]

    motions = (
        Motion.query.filter_by(meeting_id=meeting.id)
        .order_by(Motion.ordering)
        .all()
    )
    stage2 = [(m, _vote_counts(Vote.motion_id == m.id)) for m in motions]

    try:
        pdf_bytes = generate_results_pdf(meeting, stage1, stage2)
        
        # Create a safe filename
        safe_filename = f"{meeting.title.replace(' ', '_').replace('/', '-')}_final_results.pdf"
        
        # Create response with PDF data
        response = Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="{safe_filename}"',
                'Content-Type': 'application/pdf',
                'Content-Length': str(len(pdf_bytes)),
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
        )
        
        return response
        
    except Exception as e:
        # Log the error and return a simple error response
        current_app.logger.error(f"Error generating PDF: {e}")
        abort(500)


@bp.route('/results/motion/<int:motion_id>')
def public_motion_text(motion_id: int):
    """Display the final text for a motion once results are public."""
    motion = db.session.get(Motion, motion_id)
    if not motion or not motion.meeting.public_results:
        abort(404)
    text = motion.final_text_md or compile_motion_text(motion)
    return render_template(
        'public_motion.html',
        motion=motion,
        meeting=motion.meeting,
        text=text,
    )


@bp.route('/results/amendment/<int:amendment_id>')
def public_amendment_text(amendment_id: int):
    """Display amendment text once results are public."""
    amendment = db.session.get(Amendment, amendment_id)
    if not amendment or not amendment.meeting.public_results:
        abort(404)
    meeting = db.session.get(Meeting, amendment.meeting_id)
    return render_template(
        'public_amendment.html',
        amendment=amendment,
        meeting=meeting,
    )


@bp.route('/results/<int:meeting_id>/debug.pdf')
@login_required
@permission_required('manage_meetings')
def debug_pdf(meeting_id: int):
    """Debug route to check PDF generation."""
    meeting = db.session.get(Meeting, meeting_id)
    if not meeting:
        abort(404)

    # Create a simple test PDF
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet
    import io

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = [Paragraph(f"Test PDF for {meeting.title}", styles['Title'])]
    doc.build(story)
    pdf_data = buffer.getvalue()
    buffer.close()
    
    current_app.logger.info(f"Generated PDF of {len(pdf_data)} bytes")
    
    response = Response(
        pdf_data,
        mimetype='application/pdf',
        headers={
            'Content-Disposition': 'attachment; filename="test.pdf"',
            'Content-Type': 'application/pdf',
            'Content-Length': str(len(pdf_data)),
        }
    )
    
    return response
