# run.py
import threading
import schedule
import time
from datetime import datetime
from app import create_app
from app.services.subscription import SubscriptionService
from waitress import serve
from app.config import Config

app = create_app()

# スケジューラーの実行状態を管理するフラグ
scheduler_running = False

def run_schedule():
    global scheduler_running
    # 既に実行中の場合は終了
    if scheduler_running:
        return
    scheduler_running = True
    
    print(f"\n=== スケジューラー起動: {datetime.now()} ===")
    
    def check_task():
        try:
            print(f"\n=== 定期チェック実行: {datetime.now()} ===")
            SubscriptionService.check_and_process_subscriptions()
            print("=== 定期チェック完了 ===\n")
        except Exception as e:
            print(f"スケジュールタスク実行エラー: {e}")
    
    # チェックの時間間隔は「config.py」で制御
    schedule.every(Config.get_scheduler_interval()).minutes.do(check_task)
    print(f"スケジューラー: {Config.get_scheduler_interval()}分間隔で起動")
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(10)  # 10秒ごとにスケジュールをチェック
            print(".", end="", flush=True)  # 動作確認用のドット
        except Exception as e:
            print(f"スケジューラーエラー: {e}")

def start_scheduler():
    if Config.ENVIRONMENT == 'development':
        # 開発環境では親プロセスでのみスケジューラーを実行
        import os
        if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
            schedule_thread = threading.Thread(target=run_schedule)
            schedule_thread.daemon = True
            schedule_thread.start()
            print("スケジューラースレッド起動完了（開発環境）")
    else:
        # 本番環境では通常通り実行
        schedule_thread = threading.Thread(target=run_schedule)
        schedule_thread.daemon = True
        schedule_thread.start()
        print("スケジューラースレッド起動完了（本番環境）")

if __name__ == "__main__":
    print(f"アプリケーション起動: {datetime.now()}")
    print(f"環境: {Config.ENVIRONMENT}")
    
    start_scheduler()
    
    # 開発環境の場合
    if Config.ENVIRONMENT == 'development':
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:
        # 本番環境の場合はwaitressを使用
        serve(app, host='0.0.0.0', port=5000)