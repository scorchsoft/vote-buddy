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
    RUNOFF_EXTENSION_MINUTES = int(os.getenv("RUNOFF_EXTENSION_MINUTES", "2880"))
    NOTICE_PERIOD_DAYS = int(os.getenv("NOTICE_PERIOD_DAYS", "14"))
    REMINDER_HOURS_BEFORE_CLOSE = int(os.getenv("REMINDER_HOURS_BEFORE_CLOSE", "6"))
    REMINDER_COOLDOWN_HOURS = int(os.getenv("REMINDER_COOLDOWN_HOURS", "24"))
    REMINDER_TEMPLATE = os.getenv("REMINDER_TEMPLATE", "email/reminder")
    TIE_BREAK_DECISIONS = os.getenv("TIE_BREAK_DECISIONS", "{}")
    CLERICAL_TEXT = os.getenv(
        "CLERICAL_TEXT",
        "The Board may correct typographical or numbering errors with no change to meaning.",
    )
    MOVE_TEXT = os.getenv(
        "MOVE_TEXT",
        "The Board may place this change in the Articles or Bylaws as most appropriate.",
    )
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "200 per day")
    RATELIMIT_STORAGE_URL = os.getenv("RATELIMIT_STORAGE_URL", "memory://")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
