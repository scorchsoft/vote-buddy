import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///:memory:")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
    MAIL_SERVER = os.getenv("MAIL_SERVER")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 25))
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() in ["1", "true"]
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER")
    VOTE_SALT = os.getenv("VOTE_SALT", "static-salt")
    TOKEN_SALT = os.getenv("TOKEN_SALT", "token-salt")
    API_TOKEN_SALT = os.getenv("API_TOKEN_SALT", "api-token-salt")
    PASSWORD_RESET_EXPIRY_HOURS = int(os.getenv("PASSWORD_RESET_EXPIRY_HOURS", "24"))
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "instance/files")
    RUNOFF_EXTENSION_MINUTES = int(os.getenv("RUNOFF_EXTENSION_MINUTES", "2880"))
    NOTICE_PERIOD_DAYS = int(os.getenv("NOTICE_PERIOD_DAYS", "14"))
    STAGE1_LENGTH_DAYS = int(os.getenv("STAGE1_LENGTH_DAYS", "7"))
    STAGE_GAP_DAYS = int(os.getenv("STAGE_GAP_DAYS", "1"))
    STAGE2_LENGTH_DAYS = int(os.getenv("STAGE2_LENGTH_DAYS", "5"))
    MOTION_WINDOW_DAYS = int(os.getenv("MOTION_WINDOW_DAYS", "7"))  # Motion submission window
    MOTION_DEADLINE_GAP_DAYS = int(os.getenv("MOTION_DEADLINE_GAP_DAYS", "0"))  # Reduced from 7 to 0 - motions open immediately
    AMENDMENT_WINDOW_DAYS = int(os.getenv("AMENDMENT_WINDOW_DAYS", "5"))  # Extended from 1 to 5 days
    REMINDER_HOURS_BEFORE_CLOSE = int(os.getenv("REMINDER_HOURS_BEFORE_CLOSE", "6"))
    REMINDER_COOLDOWN_HOURS = int(os.getenv("REMINDER_COOLDOWN_HOURS", "24"))
    REMINDER_TEMPLATE = os.getenv("REMINDER_TEMPLATE", "email/reminder")
    STAGE2_REMINDER_HOURS_BEFORE_CLOSE = int(os.getenv("STAGE2_REMINDER_HOURS_BEFORE_CLOSE", "6"))
    STAGE2_REMINDER_COOLDOWN_HOURS = int(os.getenv("STAGE2_REMINDER_COOLDOWN_HOURS", "24"))
    STAGE2_REMINDER_TEMPLATE = os.getenv("STAGE2_REMINDER_TEMPLATE", "email/stage2_reminder")
    TIE_BREAK_DECISIONS = os.getenv("TIE_BREAK_DECISIONS", "{}")
    CLERICAL_TEXT = os.getenv(
        "CLERICAL_TEXT",
        "The Board may correct typographical or numbering errors with no change to meaning.",
    )
    MOVE_TEXT = os.getenv(
        "MOVE_TEXT",
        "The Board may place this change in the Articles or Bylaws as most appropriate.",
    )
    FINAL_STAGE_MESSAGE = (
        "**Thanks for voting!**\n\n"
        "Getting involved is important to the sport. "
        "If you don't already volunteer some time, maybe consider it—even a small commitment helps. "
        "Volunteering isn't just about refereeing or coaching; it's also about helping in other ways that help grow the sport. "
        "Let British Powerlifting know where you shine by [getting in touch](https://www.britishpowerlifting.org/contactus)."
    )
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "1000 per day")
    RATELIMIT_STORAGE_URL = os.getenv("RATELIMIT_STORAGE_URL", "memory://")
    COMMENTS_PER_PAGE = int(os.getenv("COMMENTS_PER_PAGE", "10"))
    COMMENT_EDIT_MINUTES = int(os.getenv("COMMENT_EDIT_MINUTES", "15"))
    EMAIL_WHY_TEXT = os.getenv(
        "EMAIL_WHY_TEXT",
        "You are a member of our organisation and have therefore been invited to participate in voting in AGMs/EGMs. If you do not want to participate in the process then please ignore this and subsequent emails",
    )


class DevelopmentConfig(Config):
    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True
    SEND_FILE_MAX_AGE_DEFAULT = 0


class ProductionConfig(Config):
    DEBUG = False
