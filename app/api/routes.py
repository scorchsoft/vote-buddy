from functools import wraps
import os
import yaml
from flask import request, abort, jsonify, current_app, render_template

from ..extensions import db, limiter
from ..models import Meeting, Amendment, Motion, Vote, ApiToken
from . import bp


def token_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            abort(401)
        token = auth.split(None, 1)[1]
        if not ApiToken.verify(token, current_app.config["API_TOKEN_SALT"]):
            abort(401)
        return func(*args, **kwargs)

    return wrapper


def token_key_func():
    """Rate limit key using the API token."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth.split(None, 1)[1]
    return request.remote_addr


def _vote_counts(query):
    counts = {"for": 0, "against": 0, "abstain": 0}
    rows = (
        db.session.query(Vote.choice, db.func.count(Vote.id))
        .filter(query)
        .group_by(Vote.choice)
        .all()
    )
    for choice, count in rows:
        counts[choice] = count
    return counts


@bp.get("/docs")
def api_docs():
    docs_path = os.path.join(current_app.root_path, "..", "docs", "api.yaml")
    with open(docs_path) as f:
        data = yaml.safe_load(f)
    return render_template("api_docs.html", docs=data)


@bp.get("/meetings")
@token_required
@limiter.limit("60 per minute", key_func=token_key_func)
def list_meetings():
    meetings = (
        Meeting.query.filter_by(public_results=True)
        .order_by(Meeting.title)
        .all()
    )
    return jsonify([{"id": m.id, "title": m.title} for m in meetings])


@bp.get("/meetings/<int:meeting_id>/results")
@token_required
@limiter.limit("60 per minute", key_func=token_key_func)
def meeting_results(meeting_id: int):
    meeting = Meeting.query.get_or_404(meeting_id)
    if not meeting.public_results:
        abort(404)

    tallies = []
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


@bp.get("/meetings/<int:meeting_id>/stage1-results")
@token_required
@limiter.limit("60 per minute", key_func=token_key_func)
def meeting_stage1_results(meeting_id: int):
    """Return amendment tallies if stage results are public."""
    meeting = Meeting.query.get_or_404(meeting_id)
    if not (meeting.early_public_results or meeting.public_results):
        abort(404)

    tallies = []
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

    return jsonify({"meeting_id": meeting.id, "tallies": tallies})
