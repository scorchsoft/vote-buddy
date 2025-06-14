import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///:memory:')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-me')
    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 25))
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() in ['1', 'true']
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
