"""
Pet Monitoring System - Main Orchestrator

This script runs the pet monitoring system on a scheduled basis.
It coordinates camera tracking, image capture, and Slack notifications.
"""

import os
import sys
import time
import logging
from datetime import datetime
from dotenv import load_dotenv
import schedule

from camera_tracker import CameraTracker
from slack_uploader import SlackUploader


# ログの設定
# ファイルとコンソールの両方にログを出力
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("pet_monitoring.log"),  # ファイルに保存
        logging.StreamHandler(sys.stdout),  # コンソールに出力
    ],
)
logger = logging.getLogger(__name__)


class PetMonitoringSystem:
    """ペット監視システムのメインオーケストレーター"""

    def __init__(self):
        """
        .envファイルから設定を読み込んで監視システムを初期化

        .envファイルには以下の設定が必要:
        - SLACK_BOT_TOKEN: Slackボット認証トークン
        - SLACK_CHANNEL: 通知先Slackチャンネル
        - カメラ・サーボ・画像関連の設定
        """
        # .envファイルから環境変数を読み込み
        load_dotenv()

        # ========== Slack設定 ==========
        slack_token = os.getenv("SLACK_BOT_TOKEN")
        if not slack_token:
            raise ValueError("SLACK_BOT_TOKEN not set in .env file")

        self.slack_channel = os.getenv("SLACK_CHANNEL", "#pet-monitoring")
        self.slack_uploader = SlackUploader(slack_token)

        # ========== カメラトラッカー設定 ==========
        self.camera_tracker = CameraTracker(
            model_path=os.getenv("YOLO_MODEL_PATH", "yolov8n.pt"),
            camera_index=int(os.getenv("CAMERA_INDEX", "0")),
            frame_width=int(os.getenv("FRAME_WIDTH", "640")),
            frame_height=int(os.getenv("FRAME_HEIGHT", "480")),
            kp_pan=float(os.getenv("KP_PAN", "0.02")),  # P制御ゲイン
            kp_tilt=float(os.getenv("KP_TILT", "0.02")),
            deadband=int(os.getenv("DEADBAND", "10")),  # 不感帯
        )

        # ========== 画像キャプチャ設定 ==========
        self.save_dir = os.getenv("IMAGE_SAVE_DIR", "./captured_images")
        self.capture_count = int(os.getenv("CAPTURE_COUNT", "3"))  # 撮影枚数
        self.long_edge = int(os.getenv("IMAGE_LONG_EDGE", "800"))  # リサイズ後の長辺
        self.jpeg_quality = int(os.getenv("JPEG_QUALITY", "70"))  # JPEG品質

        # ========== 追跡設定 ==========
        self.tracking_duration = float(os.getenv("TRACKING_DURATION", "8.0"))  # 追跡時間（秒）
        self.scan_steps_pan = int(os.getenv("SCAN_STEPS_PAN", "9"))  # パンスキャンステップ数
        self.scan_steps_tilt = int(os.getenv("SCAN_STEPS_TILT", "5"))  # チルトスキャンステップ数

        # ========== スケジュール設定 ==========
        self.schedule_interval = int(os.getenv("SCHEDULE_INTERVAL", "10"))  # 実行間隔（分）

        # 起動時に設定内容をログ出力
        logger.info("Pet monitoring system initialized")
        logger.info(f"Schedule interval: {self.schedule_interval} minutes")
        logger.info(f"Slack channel: {self.slack_channel}")
        logger.info(f"Image save directory: {self.save_dir}")

    def run_monitoring_cycle(self):
        """
        監視サイクルを1回実行: スキャン → 追跡 → 撮影 → アップロード

        処理フロー:
        1. カメラを動かしてペットを探す（スキャン）
        2. ペットを検出したら追跡する
        3. 静止画を3枚撮影
        4. Slackに画像をアップロード
        """
        logger.info("=" * 60)
        logger.info(f"Starting monitoring cycle at {datetime.now()}")
        logger.info("=" * 60)

        try:
            # ========== ステップ1: スキャン＆追跡 ==========
            logger.info("Step 1: Scanning for pets...")
            pet_detected = self.camera_tracker.scan_and_track(
                scan_steps_pan=self.scan_steps_pan,
                scan_steps_tilt=self.scan_steps_tilt,
                tracking_duration=self.tracking_duration,
            )

            # ペットが見つからなかった場合は終了
            if not pet_detected:
                logger.info("No pet detected during scan")
                self.camera_tracker.reset_position()  # カメラを中央に戻す
                return

            # ========== ステップ2: 画像撮影 ==========
            logger.info("Step 2: Capturing images...")
            file_paths = self.camera_tracker.capture_images(
                save_dir=self.save_dir,
                count=self.capture_count,
                long_edge=self.long_edge,
                jpeg_quality=self.jpeg_quality,
            )

            # 画像が撮影できなかった場合は終了
            if not file_paths:
                logger.warning("No images captured")
                return

            logger.info(f"Captured {len(file_paths)} images")

            # ========== ステップ3: Slackにアップロード ==========
            logger.info("Step 3: Uploading to Slack...")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = f"🐾 Pet detected at {timestamp}"

            success = self.slack_uploader.upload_files(
                file_paths=file_paths,
                channel=self.slack_channel,
                text=message,
                title="Pet Monitoring Alert",
            )

            if success:
                logger.info("Successfully uploaded images to Slack")
            else:
                logger.error("Failed to upload images to Slack")

            # ========== 後処理 ==========
            # カメラを中央位置にリセット
            self.camera_tracker.reset_position()
            logger.info("Monitoring cycle completed successfully")

        except Exception as e:
            # エラーが発生した場合の処理
            logger.error(f"Error during monitoring cycle: {e}", exc_info=True)
            try:
                # エラー時もカメラをリセット
                self.camera_tracker.reset_position()
            except Exception as reset_error:
                logger.error(f"Failed to reset camera position: {reset_error}")

    def test_system(self):
        """
        システムコンポーネントのテスト

        起動前に各コンポーネントが正常に動作するか確認:
        1. Slack接続テスト
        2. カメラテスト
        3. サーボテスト

        Returns:
            True: すべてのテストが成功
            False: いずれかのテストが失敗
        """
        logger.info("Testing system components...")

        # ========== Slack接続テスト ==========
        logger.info("Testing Slack connection...")
        if self.slack_uploader.test_connection():
            logger.info("✓ Slack connection OK")
        else:
            logger.error("✗ Slack connection failed")
            return False

        # ========== カメラテスト ==========
        logger.info("Testing camera...")
        try:
            self.camera_tracker._open_camera()
            ret, frame = self.camera_tracker.cap.read()
            self.camera_tracker._close_camera()

            if ret and frame is not None:
                logger.info(f"✓ Camera OK (resolution: {frame.shape[1]}x{frame.shape[0]})")
            else:
                logger.error("✗ Camera failed to capture frame")
                return False
        except Exception as e:
            logger.error(f"✗ Camera test failed: {e}")
            return False

        # ========== サーボテスト ==========
        logger.info("Testing servos...")
        try:
            self.camera_tracker.reset_position()
            logger.info("✓ Servos OK")
        except Exception as e:
            logger.error(f"✗ Servo test failed: {e}")
            return False

        logger.info("All system tests passed!")
        return True

    def run(self):
        """
        スケジュール実行で監視システムを起動

        処理フロー:
        1. システムテストを実行
        2. スケジューラに監視サイクルを登録
        3. 起動時に1回実行
        4. メインループで定期実行を継続
        """
        logger.info("Pet Monitoring System starting...")

        # ========== 起動前テスト ==========
        if not self.test_system():
            logger.error("System test failed. Exiting...")
            sys.exit(1)

        # ========== スケジューラ設定 ==========
        # 指定間隔（分）ごとに監視サイクルを実行
        schedule.every(self.schedule_interval).minutes.do(self.run_monitoring_cycle)

        # 起動直後に1回実行
        self.run_monitoring_cycle()

        # ========== メインループ ==========
        logger.info(f"Entering main loop (checking every {self.schedule_interval} minutes)")
        try:
            while True:
                schedule.run_pending()  # スケジュール済みタスクを実行
                time.sleep(1)  # 1秒ごとにチェック
        except KeyboardInterrupt:
            # Ctrl+Cで停止された場合
            logger.info("Shutting down...")
            self.cleanup()

    def cleanup(self):
        """
        システムリソースのクリーンアップ

        カメラを閉じて、サーボを中央位置にリセット
        """
        logger.info("Cleaning up resources...")
        try:
            self.camera_tracker.cleanup()
            logger.info("Cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


def main():
    """メインエントリーポイント"""
    try:
        # システムを初期化して実行
        system = PetMonitoringSystem()
        system.run()
    except KeyboardInterrupt:
        # ユーザーによる中断
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        # 致命的なエラー
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()