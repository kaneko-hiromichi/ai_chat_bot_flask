# app/routes/webhook.py
from flask import Blueprint, request, Response
import stripe
from ..config import Config
from ..services.subscription import SubscriptionService

bp = Blueprint('webhook', __name__)

@bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, Config.WEBHOOK_SECRET_KEY
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return '', 400

    # イベントタイプに基づいて処理
    if event['type'] == 'invoice.payment_succeeded':
        customer_id = event['data']['object']['customer']
        handle_successful_payment(customer_id)
        
    elif event['type'] == 'customer.subscription.updated':
        customer_id = event['data']['object']['customer']
        new_status = event['data']['object']['status']
        handle_subscription_update(customer_id, new_status)
        
    elif event['type'] == 'customer.subscription.deleted':
        customer_id = event['data']['object']['customer']
        handle_subscription_cancellation(customer_id)
        
    return '', 200

def handle_successful_payment(customer_id):
    """支払い成功時の処理"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # カスタマーIDに基づいてユーザーを特定
        cursor.execute(
            'SELECT email FROM user_account WHERE customer_id = %s',
            (customer_id,)
        )
        user = cursor.fetchone()
        if user:
            SubscriptionService.update_subscription_success(user['email'])
    finally:
        cursor.close()
        conn.close()

def handle_subscription_update(customer_id, new_status):
    """サブスクリプション更新時の処理"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'UPDATE user_account SET subscription_status = %s WHERE customer_id = %s',
            (new_status == 'active', customer_id)
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def handle_subscription_cancellation(customer_id):
    """サブスクリプション解約時の処理"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE user_account 
            SET subscription_status = false,
                payment_status = false
            WHERE customer_id = %s
        """, (customer_id,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()