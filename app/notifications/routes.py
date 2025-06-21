from flask import Blueprint, render_template, abort
from ..models import UnsubscribeToken, Member
from ..extensions import db

bp = Blueprint('notifications', __name__)

@bp.route('/unsubscribe/<token>')
def unsubscribe(token: str):
    token_obj = UnsubscribeToken.query.filter_by(token=token).first_or_404()
    member = db.session.get(Member, token_obj.member_id)
    if member is None:
        abort(404)
    member.email_opt_out = True
    db.session.commit()
    return render_template(
        'notifications/unsubscribed.html', member=member, token=token
    )


@bp.route('/resubscribe/<token>')
def resubscribe(token: str):
    """Allow a member to opt back in to notification emails."""
    token_obj = UnsubscribeToken.query.filter_by(token=token).first_or_404()
    member = db.session.get(Member, token_obj.member_id)
    if member is None:
        abort(404)
    member.email_opt_out = False
    db.session.commit()
    return render_template('notifications/resubscribed.html', member=member)
