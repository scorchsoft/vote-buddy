"""add performance indexes

Revision ID: i20240701
Revises: s1t2u3v4
Create Date: 2025-06-22 01:04:57.974821

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'i20240701'
down_revision = 's1t2u3v4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_members_meeting_id", "members", ["meeting_id"])
    op.create_index("ix_motions_meeting_id", "motions", ["meeting_id"])
    op.create_index("ix_amendments_meeting_id", "amendments", ["meeting_id"])
    op.create_index("ix_amendments_motion_id", "amendments", ["motion_id"])
    op.create_index("ix_vote_tokens_member_id", "vote_tokens", ["member_id"])
    op.create_index("ix_vote_tokens_stage", "vote_tokens", ["stage"])
    op.create_index("ix_submission_tokens_member_id", "submission_tokens", ["member_id"])
    op.create_index("ix_submission_tokens_meeting_id", "submission_tokens", ["meeting_id"])
    op.create_index("ix_unsubscribe_tokens_member_id", "unsubscribe_tokens", ["member_id"])
    op.create_index("ix_votes_member_id", "votes", ["member_id"])
    op.create_index("ix_votes_amendment_id", "votes", ["amendment_id"])
    op.create_index("ix_votes_motion_id", "votes", ["motion_id"])
    op.create_index("ix_comments_meeting_id", "comments", ["meeting_id"])
    op.create_index("ix_comments_motion_id", "comments", ["motion_id"])
    op.create_index("ix_comments_amendment_id", "comments", ["amendment_id"])
    op.create_index("ix_comments_member_id", "comments", ["member_id"])
    op.create_index("ix_comments_hidden", "comments", ["hidden"])
    op.create_index("ix_email_logs_meeting_id", "email_logs", ["meeting_id"])
    op.create_index("ix_email_logs_member_id", "email_logs", ["member_id"])
    op.create_index("ix_admin_logs_user_id", "admin_logs", ["user_id"])
    op.create_index("ix_motion_submissions_meeting_id", "motion_submissions", ["meeting_id"])
    op.create_index("ix_motion_submissions_member_id", "motion_submissions", ["member_id"])
    op.create_index("ix_amendment_submissions_motion_id", "amendment_submissions", ["motion_id"])
    op.create_index("ix_amendment_submissions_member_id", "amendment_submissions", ["member_id"])
    op.create_index("ix_meeting_files_meeting_id", "meeting_files", ["meeting_id"])


def downgrade():
    op.drop_index("ix_meeting_files_meeting_id", table_name="meeting_files")
    op.drop_index("ix_amendment_submissions_member_id", table_name="amendment_submissions")
    op.drop_index("ix_amendment_submissions_motion_id", table_name="amendment_submissions")
    op.drop_index("ix_motion_submissions_member_id", table_name="motion_submissions")
    op.drop_index("ix_motion_submissions_meeting_id", table_name="motion_submissions")
    op.drop_index("ix_admin_logs_user_id", table_name="admin_logs")
    op.drop_index("ix_email_logs_member_id", table_name="email_logs")
    op.drop_index("ix_email_logs_meeting_id", table_name="email_logs")
    op.drop_index("ix_comments_hidden", table_name="comments")
    op.drop_index("ix_comments_member_id", table_name="comments")
    op.drop_index("ix_comments_amendment_id", table_name="comments")
    op.drop_index("ix_comments_motion_id", table_name="comments")
    op.drop_index("ix_comments_meeting_id", table_name="comments")
    op.drop_index("ix_votes_motion_id", table_name="votes")
    op.drop_index("ix_votes_amendment_id", table_name="votes")
    op.drop_index("ix_votes_member_id", table_name="votes")
    op.drop_index("ix_unsubscribe_tokens_member_id", table_name="unsubscribe_tokens")
    op.drop_index("ix_submission_tokens_meeting_id", table_name="submission_tokens")
    op.drop_index("ix_submission_tokens_member_id", table_name="submission_tokens")
    op.drop_index("ix_vote_tokens_stage", table_name="vote_tokens")
    op.drop_index("ix_vote_tokens_member_id", table_name="vote_tokens")
    op.drop_index("ix_amendments_motion_id", table_name="amendments")
    op.drop_index("ix_amendments_meeting_id", table_name="amendments")
    op.drop_index("ix_motions_meeting_id", table_name="motions")
    op.drop_index("ix_members_meeting_id", table_name="members")
