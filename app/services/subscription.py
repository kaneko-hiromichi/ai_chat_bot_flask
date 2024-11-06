# app/services/subscription.py
from datetime import datetime, timedelta
from ..database import get_db_connection
from .stripe import StripeService
from ..config import Config

class SubscriptionService:

    @staticmethod
    def check_and_process_subscriptions():


        """サブスクリプションの自動チェックと処理"""
        print("\n=== サブスクリプション自動チェック開始 ===")
        current_time = datetime.now()
        print(f"現在時刻: {current_time}")
        
        conn = get_db_connection()
        cursor = conn.cursor()

        try:


            # 1. 解約処理対象のユーザーを処理
            print("解約予定ユーザーの確認中...")
            cursor.execute("""
                SELECT email
                FROM user_account
                WHERE 
                    next_process_date <= NOW() AT TIME ZONE 'UTC' 
                    AND next_process_type = 'cancel'
            """)
            cancellation_users = cursor.fetchall()
            
            print(f"解約対象ユーザー数: {len(cancellation_users)}")

            for user in cancellation_users:
                print(f"\n--- 解約処理開始: {user['email']} ---")
                try:
                    # 現在のプラン情報を取得
                    cursor.execute("""
                        SELECT plan, monthly_cost
                        FROM user_account
                        WHERE email = %s
                    """, (user['email'],))
                    user_data = cursor.fetchone()
                    current_plan = user_data['plan']

                    # user_payment テーブルに解約記録を追加
                    cursor.execute("""
                        INSERT INTO user_payment (
                            email,
                            plan,
                            amount,
                            payment_status,
                            next_process_date,
                            processed_by,
                            message
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s
                        )
                    """, (
                        user['email'],
                        current_plan,
                        0,            
                        False,        
                        None,        # 解約時はnext_process_dateはNULL
                        'cancellation',
                        'プラン解約'
                    ))

                    # ユーザーアカウントの更新
                    cursor.execute("""
                        UPDATE user_account 
                        SET 
                            next_process_type = NULL,
                            next_process_date = NULL,
                            payment_status = false,
                            plan = 'Free',
                            monthly_cost = 0,
                            next_plan = NULL
                        WHERE email = %s
                    """, (user['email'],))

                    conn.commit()
                    print(f"解約処理完了: {user['email']}")
                except Exception as e:
                    print(f"解約処理エラー: {e}")
                    conn.rollback()


            print("プラン変更予定ユーザーの確認中...")
            cursor.execute("""
                SELECT 
                    email,
                    plan,
                    next_plan,
                    monthly_cost,
                    next_process_date,
                    next_process_type
                FROM user_account
                WHERE 
                    next_process_date <= NOW() AT TIME ZONE 'UTC'
                    AND next_process_type = 'plan_change'
                    AND payment_status = true
            """)
            plan_change_users = cursor.fetchall()
            
            print(f"プラン変更対象ユーザー数: {len(plan_change_users)}")
            
            for user in plan_change_users:
                print(f"\n--- プラン変更処理開始: {user['email']} ---")
                print(f"現在のプラン: {user['plan']}")
                print(f"変更後のプラン: {user['next_plan']}")
                print(f"処理予定日: {user['next_process_date']}")
                
                # 新しいプランの金額を取得
                new_plan_details = Config.SUBSCRIPTION_PLANS.get(user['next_plan'])
                if not new_plan_details:
                    print(f"エラー: 無効なプラン {user['next_plan']}")
                    continue
                    
                amount = new_plan_details['price']
                print(f"請求金額: ¥{amount}")
                
                try:
                    # Stripe決済処理
                    print(f"Stripe決済処理開始: {user['email']}")
                    success, transaction_id, error_message = StripeService.process_subscription_payment(
                        user['email'],
                        amount
                    )
                    if not success:
                        print(f"決済エラー: {error_message}")
                    
                except Exception as e:
                    success = False
                    transaction_id = None
                    error_message = str(e)
                    print(f"決済エラー: {error_message}")

                # プラン変更の記録
                try:
                    cursor.execute("""
                        INSERT INTO user_payment (
                            email,
                            plan,
                            amount,
                            payment_status,
                            next_process_date,
                            processed_by,
                            transaction_id,
                            message
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s
                        ) RETURNING id
                    """, (
                        user['email'],
                        user['next_plan'],  # 新しいプラン名
                        amount,
                        success,
                        user['next_process_date'],
                        'plan_change',
                        transaction_id,
                        f'{user["plan"]}から{user["next_plan"]}へのプラン変更' if success else error_message
                    ))
                    payment_record = cursor.fetchone()
                    print(f"プラン変更記録作成: ID {payment_record['id']}")

                    if success:
                        print("決済成功")
                        cursor.execute("""
                            UPDATE user_account 
                            SET 
                                plan = next_plan,
                                next_plan = NULL,
                                next_process_type = 'payment',
                                monthly_cost = 0,
                                next_process_date = NOW() + INTERVAL %s,
                                last_payment_date = NOW()
                            WHERE email = %s
                            RETURNING plan, next_plan, next_process_date
                        """, (Config.get_next_payment_interval(), user['email']))
                        updated = cursor.fetchone()
                        print(f"プラン変更完了: {updated['plan']}")
                        print(f"次回支払い日を更新: {updated['next_process_date']}")
                    else:
                        print("決済失敗")
                        cursor.execute("""
                            UPDATE user_account 
                            SET 
                                payment_status = false,
                                next_process_type = NULL,
                                next_plan = NULL
                            WHERE email = %s
                        """, (user['email'],))
                        print("プラン変更キャンセル")
                        
                    conn.commit()
                except Exception as e:
                    print(f"プラン変更記録作成エラー: {e}")
                    conn.rollback()
                    continue

                print(f"--- プラン変更処理完了: {user['email']} ---")


            

            # 2. 支払い対象のユーザーを処理
            print("\n支払い期限チェック中...")
            # subscription.py の支払い対象ユーザー取得クエリを修正
            cursor.execute("""
                SELECT 
                    email, 
                    plan, 
                    monthly_cost,
                    next_process_date,
                    next_process_type
                FROM user_account
                WHERE 
                    next_process_date <= NOW()
                    AND payment_status = true
                    AND next_process_type = 'payment'
                    AND NOT EXISTS (
                        SELECT 1 
                        FROM user_payment 
                        WHERE user_payment.email = user_account.email 
                        AND processed_date >= NOW() - INTERVAL '5 minutes'
                    )
            """)
            payment_users = cursor.fetchall()
            
            print(f"支払い対象ユーザー数: {len(payment_users)}")
            
            for user in payment_users:
                print(f"\n--- ユーザー処理開始: {user['email']} ---")
                print(f"現在のプラン: {user['plan']}")
                print(f"次回処理予定日: {user['next_process_date']}")  # ここを修正
                print(f"現在の利用額: {user['monthly_cost']}")
                
                plan_details = Config.SUBSCRIPTION_PLANS.get(user['plan'])
                if not plan_details:
                    print(f"エラー: 無効なプラン {user['plan']}")
                    continue
                    
                amount = plan_details['price']
                print(f"請求金額: ¥{amount}")
                
                try:
                    # Stripe決済処理
                    print(f"Stripe決済処理開始: {user['email']}")
                    success, transaction_id, error_message = StripeService.process_subscription_payment(
                        user['email'],
                        amount
                    )
                    if not success:
                        print(f"決済エラー: {error_message}")
                    
                except Exception as e:
                    success = False
                    transaction_id = None
                    error_message = str(e)
                    print(f"決済エラー: {error_message}")

                # サブスクリプション支払いの記録
                try:
                    next_process_date = datetime.now() + timedelta(minutes=3)  # テスト用1分後
                    cursor.execute("""
                        INSERT INTO user_payment (
                            email,
                            plan,
                            amount,
                            payment_status,
                            next_process_date,
                            processed_by,
                            transaction_id,
                            message
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s
                        ) RETURNING id
                    """, (
                        user['email'],
                        user['plan'],
                        amount,
                        success,
                        next_process_date,
                        'auto_subscription',
                        transaction_id,
                        '定期支払い' if success else error_message
                    ))
                    payment_record = cursor.fetchone()
                    print(f"サブスクリプション支払い記録作成: ID {payment_record['id']}")

                except Exception as e:
                    print(f"支払い記録作成エラー: {e}")
                    continue

                if success:
                    print("決済成功")
                    cursor.execute("""
                        UPDATE user_account 
                        SET 
                            last_payment_date = NOW(),
                            next_process_date = NOW() + INTERVAL %s,
                            payment_status = true,
                            monthly_cost = 0
                        WHERE email = %s
                        RETURNING next_process_date, monthly_cost
                    """, (Config.get_next_payment_interval(), user['email']))
                    updated = cursor.fetchone()
                    print(f"次回処理日を更新: {updated['next_process_date']}")
                    print(f"利用額をリセット: {updated['monthly_cost']}")
                else:
                    print("決済失敗")
                    cursor.execute("""
                        UPDATE user_account 
                        SET 
                            payment_status = false,
                            next_process_date = NULL,
                            next_process_type = NULL
                        WHERE email = %s
                    """, (user['email'],))
                    print("サブスクリプション停止")
                conn.commit()
                print(f"--- ユーザー処理完了: {user['email']} ---")

            print(f"全ユーザーの処理が完了しました")

        except Exception as e:
            print(f"エラー発生: {e}")
            print(f"エラータイプ: {type(e)}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
            print("=== サブスクリプション自動チェック完了 ===\n")

    @staticmethod
    def notify_payment_failure(email):
        """支払い失敗時のユーザー通知"""
        # TODO: メール通知の実装
        pass

    @staticmethod
    def handle_subscription_cancellation(email):
        """サブスクリプション解約処理"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE user_account 
                SET 
                    subscription_status = false,
                    payment_status = false,
                    plan = 'Free'
                WHERE email = %s
            """, (email,))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error cancelling subscription: {e}")
            return False
        finally:
            cursor.close()
            conn.close()