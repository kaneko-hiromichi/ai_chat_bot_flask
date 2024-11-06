# app/services/auth.py
from datetime import datetime, timedelta
from bcrypt import hashpw, gensalt, checkpw
from ..database import execute_query
from ..config import Config 

class AuthService:
  
    @staticmethod
    def login(email, password):
        """
        ユーザーログイン処理
        """
        query = """
            SELECT password_hash, login_attempts, last_attempt_time, unlock_token 
            FROM user_account 
            WHERE email = %s
        """
        
        print(f"Login attempt for email: {email}")  # デバッグ用
        result = execute_query(query, (email,))
        print(f"Raw query result: {result}")  # デバッグ用
        
        if not result:
            return False, "ユーザーが見つかりません"
        
        if not isinstance(result, list) or len(result) == 0:
            return False, "ユーザーが見つかりません"
            
        user = result[0]  # 最初の結果を取得
        print(f"User data: {user}")  # デバッグ用
            
        # ロックアウトチェック
        if user['login_attempts'] >= Config.MAX_LOGIN_ATTEMPTS:
            if user['last_attempt_time']:
                lockout_time = user['last_attempt_time'] + timedelta(minutes=Config.LOCKOUT_TIME)
                if datetime.now() < lockout_time:
                    return False, "アカウントがロックされました。メールをご確認ください。"

        # パスワードチェック
        try:
            if checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                # ログイン成功時の処理
                execute_query("""
                    UPDATE user_account 
                    SET login_attempts = 0, 
                        last_attempt_time = NULL, 
                        unlock_token = NULL 
                    WHERE email = %s
                """, (email,))
                return True, "ログイン成功"
            else:
                # ログイン失敗時の処理
                new_attempts = user['login_attempts'] + 1
                execute_query("""
                    UPDATE user_account 
                    SET login_attempts = %s, 
                        last_attempt_time = %s 
                    WHERE email = %s
                """, (new_attempts, datetime.now(), email))
                
                return False, f"パスワードが間違っています {new_attempts}/{Config.MAX_LOGIN_ATTEMPTS}"
        except Exception as e:
            print(f"Password check error: {e}")  # デバッグ用
            return False, "認証エラーが発生しました"
    
    @staticmethod
    def signup(email, username, password, plan='basic'):
        """
        新規ユーザー登録
        """
        hashed_password = hashpw(password.encode('utf-8'), gensalt()).decode('utf-8')
        current_time = datetime.now()
        
        query = """
            INSERT INTO user_account (
                email, username, password_hash, plan, 
                payment_status, monthly_cost, created_at, last_login
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (email, username, hashed_password, plan, False, 0.0, current_time, current_time)
        
        result = execute_query(query, params)
        return result is not None
    
    @staticmethod
    def unlock_account(email):
        """アカウントロック解除"""
        return execute_query("""
            UPDATE user_account 
            SET login_attempts = 0, 
                last_attempt_time = NULL, 
                unlock_token = NULL 
            WHERE email = %s
        """, (email,))

    @staticmethod
    def reset_password(email, new_password):
        """パスワードリセット"""
        hashed_password = hashpw(new_password.encode('utf-8'), gensalt())
        return execute_query("""
            UPDATE user_account 
            SET password_hash = %s 
            WHERE email = %s
        """, (hashed_password.decode('utf-8'), email))