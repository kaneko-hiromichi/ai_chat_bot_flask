# app/routes/payment.py
from flask import Blueprint, request, jsonify
from ..services.stripe import StripeService
from ..services.subscription import SubscriptionService
from ..database import get_db_connection
from datetime import datetime, timedelta

bp = Blueprint('payment', __name__)


# =============20241105==============================================

# 解約手続き
@bp.route('/reserve-cancellation', methods=['POST'])
def reserve_cancellation():
    data = request.json
    email = data.get('email')
    
    if not email:
        return jsonify({"error": "Email is required"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 現在の支払い日を取得して次回の処理日として設定
        cursor.execute("""
            UPDATE user_account 
            SET 
                next_process_type = 'cancel',
                next_plan = NULL
            WHERE email = %s
            RETURNING next_process_date
        """, (email,))
        
        conn.commit()
        return jsonify({"message": "Cancellation reserved"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()
# ===================================================================






@bp.route('/get/user_status', methods=['GET'])
def get_user_status():
    email = request.args.get('email')
    if not email:
        return jsonify({"error": "Email is required"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT 
                plan, 
                payment_status, 
                next_process_date AT TIME ZONE 'UTC' as next_process_date,
                next_process_type,
                next_plan
            FROM user_account 
            WHERE email = %s
        """, (email,))
        
        user_data = cursor.fetchone()
        
        # 日付を ISO 8601 形式に変換
        if user_data and user_data['next_process_date']:
            user_data['next_process_date'] = user_data['next_process_date'].isoformat()
        
        return jsonify(user_data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()
        conn.close()

@bp.route('/reserve-plan-change', methods=['POST'])
def reserve_plan_change():
    data = request.json
    email = data.get('email')
    new_plan = data.get('new_plan')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 現在の支払い日を取得
        cursor.execute("""
            SELECT next_process_date 
            FROM user_account 
            WHERE email = %s
        """, (email,))
        current_data = cursor.fetchone()
        
        # プラン変更を予約
        cursor.execute("""
            UPDATE user_account 
            SET 
                next_plan = %s,
                next_process_type = 'plan_change'
            WHERE email = %s
        """, (new_plan, email))
        
        conn.commit()
        return jsonify({"message": "Plan change reserved"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp.route('/test/check-subscriptions', methods=['POST'])
def test_check_subscriptions():
    """テスト用: 手動でサブスクリプションチェックを実行"""
    try:
        SubscriptionService.manual_check()
        return jsonify({"message": "Subscription check completed"}), 200
    except Exception as e:
        print(f"Error in manual check: {e}")
        return jsonify({"error": str(e)}), 500


# payment.py の create_payment_intent
@bp.route('/create-payment-intent', methods=['POST'])
def create_payment_intent():
    print("支払いインテントの作成エンドポイントが呼び出されました。")
    try:
        data = request.json
        amount = data.get('amount')
        email = data.get('email')
        plan = data.get('plan')
        process_type = data.get('process_type', 'payment')

        if not amount or not email or not plan:
            return jsonify({"error": "amount, email and plan are required"}), 400

        print(f"支払いインテントの作成: 金額={amount}, プラン={plan}, 処理タイプ={process_type}")

        try:
            # Stripe PaymentIntent作成
            result = StripeService.create_payment_intent(amount, email)
            payment_intent_id = result.get('payment_intent_id')
            
            # データベース更新
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                # user_accountテーブルの更新
                cursor.execute("""
                    UPDATE user_account 
                    SET 
                        next_process_date = NOW() + INTERVAL '1 minute',
                        next_process_type = %s
                    WHERE email = %s
                """, (process_type, email))

                # 支払い記録の作成
                StripeService.record_payment(
                    email=email,
                    plan=plan,
                    amount=amount,
                    payment_status=False,
                    next_process_date=datetime.now() + timedelta(minutes=1),
                    transaction_id=payment_intent_id,
                    message='支払い処理中'
                )
                
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                cursor.close()
                conn.close()
            
            return jsonify({
                'client_secret': result['client_secret']
            }), 200
            
        except Exception as e:
            print(f"Stripe処理エラー: {e}")
            raise
            
    except Exception as e:
        print(f"エラー: 支払いインテントの作成に失敗: {str(e)}")
        return jsonify({"error": str(e)}), 400

@bp.route('/create-subscription', methods=['POST'])
def create_subscription():
    data = request.json
    email = data.get('email')
    
    try:
        customer = StripeService.create_customer(email)
        subscription = StripeService.create_subscription(
            customer.id,
            'your_price_id'  # Stripeダッシュボードの価格ID
        )
        return jsonify({
            'subscription_id': subscription.id,
            'client_secret': subscription.latest_invoice.payment_intent.client_secret
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/update/plan', methods=['POST'])
def update_plan():
    data = request.json
    email = data.get('email')
    new_plan = data.get('plan')
    process_type = data.get('process_type', 'payment')  # 追加

    if not email or not new_plan:
        return jsonify({"error": "Invalid data"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE user_account 
            SET 
                plan = %s,
                next_process_date = NOW() + INTERVAL '1 minute',
                next_process_type = %s,
                last_payment_date = NOW()
            WHERE email = %s
        """, (new_plan, process_type, email))
        
        conn.commit()
        return jsonify({"message": "Plan updated successfully"}), 200
    except Exception as e:
        print(f"Error updating plan: {e}")
        return jsonify({"error": "Failed to update plan"}), 500
    finally:
        cursor.close()
        conn.close()

@bp.route('/update/payment_status', methods=['POST'])
def update_payment_status():
    data = request.json
    email = data.get('email')
    payment_status = data.get('payment_status')

    if not email or payment_status is None:
        return jsonify({"error": "Invalid data"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # トランザクション開始
        cursor.execute("BEGIN")
        
        # user_accountテーブルの更新
        cursor.execute("""
            UPDATE user_account 
            SET 
                payment_status = %s,
                next_process_type = CASE 
                    WHEN %s = true THEN 'payment'
                    ELSE NULL 
                END
            WHERE email = %s
        """, (payment_status, payment_status, email))
        
        # user_paymentテーブルの更新
        cursor.execute("""
            UPDATE user_payment 
            SET 
                payment_status = %s,
                updated_at = NOW()
            WHERE email = %s 
            AND id = (
                SELECT id FROM user_payment 
                WHERE email = %s 
                ORDER BY created_at DESC 
                LIMIT 1
            )
        """, (payment_status, email, email))
        
        cursor.execute("COMMIT")
        print(f"支払い状態を更新: email={email}, status={payment_status}")
        return jsonify({"message": "Payment status updated successfully"}), 200
    except Exception as e:
        cursor.execute("ROLLBACK")
        print(f"Error updating payment status: {e}")
        return jsonify({"error": "Failed to update payment status"}), 500
    finally:
        cursor.close()
        conn.close()