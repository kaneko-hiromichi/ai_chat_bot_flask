# app/services/user.py
from ..database import get_db_connection

class UserService:
    @staticmethod
    def update_user_data(column, value, email, increment=False):
        """
        ユーザーデータの更新
        Args:
            column (str): 更新するカラム名
            value: 新しい値
            email (str): ユーザーのメールアドレス
            increment (bool): 値を増分するかどうか
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            if increment:
                cursor.execute(f'SELECT {column} FROM user_account WHERE email = %s', (email,))
                current_value = cursor.fetchone()[column]
                new_value = current_value + value
                cursor.execute(
                    f'UPDATE user_account SET {column} = %s WHERE email = %s',
                    (new_value, email)
                )
            else:
                cursor.execute(
                    f'UPDATE user_account SET {column} = %s WHERE email = %s',
                    (value, email)
                )
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating {column}: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_user_config(email):
        """ユーザー設定の取得"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'SELECT * FROM user_account WHERE email = %s',
                (email,)
            )
            user_data = cursor.fetchone()
            if user_data:
                return {
                    'user_name': user_data.get('user_name', ''),
                    'isDarkMode': user_data.get('isdarkmode', False),
                    'selectedModel': user_data.get('selectedmodel', 'gpt-4o-mini'),
                    'chat_history_max_length': user_data.get('chat_history_max_length', 1000),
                    'input_text_length': user_data.get('input_text_length', 200),
                    'monthly_cost': user_data.get('monthly_cost', 0.0),
                    'plan': user_data.get('plan', 'basic'),
                    'sortOrder': user_data.get('sortorder', 'created_at ASC'),
                }
            return None
        finally:
            cursor.close()
            conn.close()