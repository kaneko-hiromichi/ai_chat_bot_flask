# app/database.py
import psycopg2
from psycopg2.extras import RealDictCursor
from .config import Config

def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=Config.DB_HOST,
            database=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            cursor_factory=RealDictCursor
        )
        return conn
    except psycopg2.OperationalError as e:
        print(f"Database connection error: {e}")
        return None

def execute_query(query, params=None):
    conn = get_db_connection()
    if conn is None:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        # SELECT クエリの場合
        if query.strip().upper().startswith('SELECT'):
            result = cursor.fetchall()
            print(f"Query result: {result}")  # デバッグ用
            return result
        # INSERT/UPDATE/DELETE クエリの場合
        else:
            conn.commit()
            return True
            
    except Exception as e:
        print(f"Query execution error: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()