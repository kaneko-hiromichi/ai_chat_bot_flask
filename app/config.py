# app/config.py
import os
from dotenv import load_dotenv

# .envファイルの読み込み
load_dotenv()

class Config:


    INTERVALS = {
            'production': {
                'scheduler': 1,      # スケジューラーの実行間隔（分）
                'process': "1 month" # 次回処理日までの間隔
            },
            'development': {
                'scheduler': 1,      # スケジューラーの実行間隔（分）
                'process': "3 minute" # 次回処理日までの間隔
            }
        }
    
    # 環境変数から現在の環境を取得（デフォルトは'development'）
    ENVIRONMENT = os.getenv('FLASK_ENV', 'development')
        
    @staticmethod
    def get_scheduler_interval():
        """スケジューラーの実行間隔を返す"""
        return Config.INTERVALS[Config.ENVIRONMENT]['scheduler']

    @staticmethod
    def get_next_process_interval():
        """次回処理日までの間隔を返す"""
        return Config.INTERVALS[Config.ENVIRONMENT]['process']
        

    # Flask設定
    SECRET_KEY = os.getenv('SECRET_KEY')
    
    # データベース設定
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_NAME = os.getenv('DB_NAME', 'ai_chat_app_test')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    
    # Stripe設定
    STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
    WEBHOOK_SECRET_KEY = os.getenv('WEBHOOK_SECRET_KEY')
    
    # メール設定
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'hiromichi.works@gmail.com'
    MAIL_PASSWORD = os.getenv('APP_EMAIL_PASSWORD')
    
    # ユーザー認証設定
    MAX_LOGIN_ATTEMPTS = 3
    LOCKOUT_TIME = 15  # minutes
    PASSWORD_RESET_TIMEOUT = 3600  # seconds
    
    # サブスクリプション設定
    SUBSCRIPTION_PLANS = {
        'Free': {'price': 0, 'points': 1000},
        'Light': {'price': 980, 'points': 5000},
        'Standard': {'price': 1980, 'points': 15000},
        'Pro': {'price': 2980, 'points': 30000},
        'Expert': {'price': 3980, 'points': 50000}
    }
    
    # トークン設定
    DEFAULT_INPUT_LENGTH = 200
    DEFAULT_HISTORY_LENGTH = 1000
    DEFAULT_SORT_ORDER = 'created_at ASC'
    
    # APIモデル設定
    AVAILABLE_MODELS = [
        'gpt-4',
        'gpt-3.5-turbo',
        'gpt-4o-mini'
    ]
    DEFAULT_MODEL = 'gpt-4o-mini'

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False

class TestingConfig(Config):
    DEBUG = True
    TESTING = True

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False

# 環境に応じた設定の選択
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}