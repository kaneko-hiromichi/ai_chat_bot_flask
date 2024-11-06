# app/services/stripe.py
import stripe
from ..config import Config  
from flask import current_app
from ..database import get_db_connection

def init_app(app):
    stripe.api_key = Config.STRIPE_SECRET_KEY

class StripeService:
    @staticmethod
    def create_payment_intent(amount, email):
        try:
            print(f"支払いインテント作成開始: email={email}, amount={amount}")
            
            # 顧客情報を作成または取得
            customers = stripe.Customer.list(email=email, limit=1)
            if customers.data:
                customer = customers.data[0]
                print(f"既存の顧客を使用: {customer.id}")
            else:
                customer = stripe.Customer.create(email=email)
                print(f"新規顧客を作成: {customer.id}")

            # 支払いインテントを作成
            payment_intent = stripe.PaymentIntent.create(
                amount=amount,
                currency='jpy',
                customer=customer.id,
                payment_method_types=['card'],
                setup_future_usage='off_session'  # 重要：将来の自動決済のために保存
            )
            
            # customer_idを保存（これが重要な追加部分）
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    UPDATE user_account 
                    SET customer_id = %s 
                    WHERE email = %s
                """, (customer.id, email))
                conn.commit()
                print(f"customer_id保存完了: {customer.id}")
            finally:
                cursor.close()
                conn.close()
            
            return {
                'client_secret': payment_intent.client_secret,
                'payment_intent_id': payment_intent.id
            }
        except Exception as e:
            print(f"Stripe処理エラー: {e}")
            raise

    @staticmethod
    def process_subscription_payment(email, amount):
        try:
            print(f"サブスクリプション支払い処理開始: email={email}, amount={amount}")
            
            # 1. カスタマー情報の取得または作成
            customers = stripe.Customer.list(email=email, limit=1)
            if customers.data:
                customer = customers.data[0]
                print(f"既存の顧客を使用: {customer.id}")
            else:
                customer = stripe.Customer.create(email=email)
                print(f"新規顧客を作成: {customer.id}")
                
            # 2. 支払い方法の取得
            payment_methods = stripe.PaymentMethod.list(
                customer=customer.id,
                type='card'
            )
            
            if not payment_methods.data:
                print("登録されたカードが見つかりません")
                return False, None, "登録されたカードが見つかりません"
                
            payment_method = payment_methods.data[0]
            print(f"支払い方法を使用: {payment_method.id}, カード: {payment_method.card.brand} **** {payment_method.card.last4}")

            # 3. 支払い処理
            payment_intent = stripe.PaymentIntent.create(
                amount=amount,
                currency="jpy",
                customer=customer.id,
                payment_method=payment_method.id,
                off_session=True,
                confirm=True,
            )
            
            success = payment_intent.status == 'succeeded'
            transaction_id = payment_intent.id
            print(f"支払い処理結果: success={success}, id={transaction_id}")
            
            # 4. user_accountテーブルのcustomer_id更新
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    UPDATE user_account 
                    SET customer_id = %s 
                    WHERE email = %s
                """, (customer.id, email))
                conn.commit()
            finally:
                cursor.close()
                conn.close()
                
            return success, transaction_id, None
                
        except stripe.error.CardError as e:
            print(f"カードエラー: {e}")
            return False, None, str(e)
        except Exception as e:
            print(f"支払い処理エラー: {e}")
            return False, None, str(e)
        
        
    @staticmethod
    def record_payment(email, plan, amount, payment_status, next_process_date, transaction_id=None, message=None):
        """支払い情報をuser_paymentテーブルに記録"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO user_payment (
                    email,
                    plan,
                    amount,
                    payment_status,
                    next_process_date,
                    transaction_id,
                    message,
                    processed_by
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING id
            """, (
                email,
                plan,
                amount,
                payment_status,
                next_process_date,
                transaction_id,
                message,
                'payment'
            ))
            
            payment_record = cursor.fetchone()
            conn.commit()
            print(f"支払い記録作成: ID {payment_record['id']}")
            return payment_record['id']
        except Exception as e:
            print(f"支払い記録作成エラー: {e}")
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()