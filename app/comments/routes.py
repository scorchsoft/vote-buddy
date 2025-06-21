from flask import (
    render_template,
    request,
    abort,
    redirect,
    url_for,
    current_app,
    g,
    flash,
)
from . import bp
from ..models import (
    VoteToken,
    Member,
    Meeting,
    Motion,
    Amendment,
    Comment,
    CommentRevision,
)
from ..extensions import db, limiter
from ..utils import markdown_to_html
from datetime import datetime


def _verify_token(token: str) -> tuple[Member, Meeting]:
    vote_token = VoteToken.verify(token, current_app.config["TOKEN_SALT"])
    if not vote_token:
        abort(404)
    member = db.session.get(Member, vote_token.member_id)
    if not member or not member.can_comment:
        abort(403)
    meeting = db.session.get(Meeting, member.meeting_id)
    if not meeting or not meeting.comments_enabled:
        abort(403)
    g.member_id = member.id
    return member, meeting


def _editing_allowed(comment: Comment, meeting: Meeting) -> bool:
    minutes = current_app.config.get("COMMENT_EDIT_MINUTES", 15)
    return comment.can_edit(meeting, minutes)


@bp.get("/<token>/motion/<int:motion_id>")
def motion_comments(token: str, motion_id: int):
    member, meeting = _verify_token(token)
    motion = db.session.get(Motion, motion_id)
    if not motion or motion.meeting_id != meeting.id:
        abort(404)
    page = request.args.get("page", 1, type=int)
    per_page = current_app.config.get("COMMENTS_PER_PAGE", 10)
    query = Comment.query.filter_by(motion_id=motion.id, hidden=False)
    pagination = query.order_by(Comment.created_at).paginate(
        page=page, per_page=per_page, error_out=False
    )
    comments = pagination.items
    return render_template(
        "comments/comments.html",
        comments=comments,
        pagination=pagination,
        token=token,
        target=("motion", motion.id),
        meeting=meeting,
    )


@bp.post("/<token>/motion/<int:motion_id>")
@limiter.limit("5 per minute")
def add_motion_comment(token: str, motion_id: int):
    member, meeting = _verify_token(token)
    motion = db.session.get(Motion, motion_id)
    if not motion or motion.meeting_id != meeting.id:
        abort(404)
    text = request.form.get("text", "").strip()
    if text:
        comment = Comment(
            meeting_id=meeting.id,
            motion_id=motion.id,
            member_id=member.id,
            text_md=text,
            created_at=datetime.utcnow(),
        )
        db.session.add(comment)
        db.session.commit()
        flash("Comment posted", "success")
    return redirect(url_for("comments.motion_comments", token=token, motion_id=motion.id))


@bp.get("/<token>/amendment/<int:amendment_id>")
def amendment_comments(token: str, amendment_id: int):
    member, meeting = _verify_token(token)
    amendment = db.session.get(Amendment, amendment_id)
    if not amendment or amendment.meeting_id != meeting.id:
        abort(404)
    page = request.args.get("page", 1, type=int)
    per_page = current_app.config.get("COMMENTS_PER_PAGE", 10)
    query = Comment.query.filter_by(amendment_id=amendment.id, hidden=False)
    pagination = query.order_by(Comment.created_at).paginate(
        page=page, per_page=per_page, error_out=False
    )
    comments = pagination.items
    return render_template(
        "comments/comments.html",
        comments=comments,
        pagination=pagination,
        token=token,
        target=("amendment", amendment.id),
        meeting=meeting,
    )


@bp.post("/<token>/amendment/<int:amendment_id>")
@limiter.limit("5 per minute")
def add_amendment_comment(token: str, amendment_id: int):
    member, meeting = _verify_token(token)
    amendment = db.session.get(Amendment, amendment_id)
    if not amendment or amendment.meeting_id != meeting.id:
        abort(404)
    text = request.form.get("text", "").strip()
    if text:
        comment = Comment(
            meeting_id=meeting.id,
            amendment_id=amendment.id,
            member_id=member.id,
            text_md=text,
            created_at=datetime.utcnow(),
        )
        db.session.add(comment)
        db.session.commit()
        flash("Comment posted", "success")
    return redirect(
        url_for("comments.amendment_comments", token=token, amendment_id=amendment.id)
    )


from flask_login import login_required
from ..permissions import permission_required


@bp.post("/hide/<int:comment_id>")
@login_required
@permission_required("manage_meetings")
def hide_comment(comment_id: int):
    comment = db.session.get(Comment, comment_id)
    if not comment:
        abort(404)
    comment.hidden = True
    db.session.commit()
    return "", 204


@bp.post("/member/<int:member_id>/toggle")
@login_required
@permission_required("manage_meetings")
def toggle_member_commenting(member_id: int):
    member = db.session.get(Member, member_id)
    if not member:
        abort(404)
    member.can_comment = not member.can_comment
    db.session.commit()
    return redirect(request.referrer or url_for("meetings.list_meetings"))


@bp.get("/<token>/edit/<int:comment_id>")
def edit_comment_form(token: str, comment_id: int):
    member, meeting = _verify_token(token)
    comment = db.session.get(Comment, comment_id)
    if not comment or comment.member_id != member.id:
        abort(404)
    if not _editing_allowed(comment, meeting):
        abort(403)
    target = ("motion", comment.motion_id) if comment.motion_id else ("amendment", comment.amendment_id)
    return render_template(
        "comments/edit_comment.html",
        comment=comment,
        token=token,
        target=target,
    )


@bp.post("/<token>/edit/<int:comment_id>")
def edit_comment(token: str, comment_id: int):
    member, meeting = _verify_token(token)
    comment = db.session.get(Comment, comment_id)
    if not comment or comment.member_id != member.id:
        abort(404)
    if not _editing_allowed(comment, meeting):
        abort(403)
    text = request.form.get("text", "").strip()
    if text and text != comment.text_md:
        rev = CommentRevision(comment_id=comment.id, text_md=comment.text_md, edited_at=datetime.utcnow())
        db.session.add(rev)
        comment.text_md = text
        comment.edited_at = datetime.utcnow()
        db.session.commit()
        flash("Comment updated", "success")
    target = ("motion", comment.motion_id) if comment.motion_id else ("amendment", comment.amendment_id)
    if target[0] == "motion":
        return redirect(url_for("comments.motion_comments", token=token, motion_id=target[1]))
    else:
        return redirect(url_for("comments.amendment_comments", token=token, amendment_id=target[1]))
