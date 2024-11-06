# app/__init__.py
from flask import Flask
from flask_cors import CORS
from .config import Config

def create_app(config_class=Config):
    """
    アプリケーションファクトリ
    """
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # CORS設定
    CORS(app, resources={r"/*": {"origins": "*"}})
    
    # 各種初期化
    from .services import stripe
    stripe.init_app(app)
    
    # Blueprintの登録
    from .routes import auth, user, payment, webhook
    app.register_blueprint(auth.bp)
    app.register_blueprint(user.bp)
    app.register_blueprint(payment.bp)
    app.register_blueprint(webhook.bp)
    
    return app