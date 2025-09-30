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


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("pet_monitoring.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class PetMonitoringSystem:
    """Main orchestrator for pet monitoring system."""

    def __init__(self):
        """Initialize the monitoring system with configuration from .env."""
        # Load environment variables
        load_dotenv()

        # Slack configuration
        slack_token = os.getenv("SLACK_BOT_TOKEN")
        if not slack_token:
            raise ValueError("SLACK_BOT_TOKEN not set in .env file")

        self.slack_channel = os.getenv("SLACK_CHANNEL", "#pet-monitoring")
        self.slack_uploader = SlackUploader(slack_token)

        # Camera tracker configuration
        self.camera_tracker = CameraTracker(
            model_path=os.getenv("YOLO_MODEL_PATH", "yolov8n.pt"),
            camera_index=int(os.getenv("CAMERA_INDEX", "0")),
            frame_width=int(os.getenv("FRAME_WIDTH", "640")),
            frame_height=int(os.getenv("FRAME_HEIGHT", "480")),
            kp_pan=float(os.getenv("KP_PAN", "0.02")),
            kp_tilt=float(os.getenv("KP_TILT", "0.02")),
            deadband=int(os.getenv("DEADBAND", "10")),
        )

        # Image capture configuration
        self.save_dir = os.getenv("IMAGE_SAVE_DIR", "./captured_images")
        self.capture_count = int(os.getenv("CAPTURE_COUNT", "3"))
        self.long_edge = int(os.getenv("IMAGE_LONG_EDGE", "800"))
        self.jpeg_quality = int(os.getenv("JPEG_QUALITY", "70"))

        # Tracking configuration
        self.tracking_duration = float(os.getenv("TRACKING_DURATION", "8.0"))
        self.scan_steps_pan = int(os.getenv("SCAN_STEPS_PAN", "9"))
        self.scan_steps_tilt = int(os.getenv("SCAN_STEPS_TILT", "5"))

        # Schedule interval (minutes)
        self.schedule_interval = int(os.getenv("SCHEDULE_INTERVAL", "10"))

        logger.info("Pet monitoring system initialized")
        logger.info(f"Schedule interval: {self.schedule_interval} minutes")
        logger.info(f"Slack channel: {self.slack_channel}")
        logger.info(f"Image save directory: {self.save_dir}")

    def run_monitoring_cycle(self):
        """Execute one monitoring cycle: scan, track, capture, and upload."""
        logger.info("=" * 60)
        logger.info(f"Starting monitoring cycle at {datetime.now()}")
        logger.info("=" * 60)

        try:
            # Step 1: Scan and track
            logger.info("Step 1: Scanning for pets...")
            pet_detected = self.camera_tracker.scan_and_track(
                scan_steps_pan=self.scan_steps_pan,
                scan_steps_tilt=self.scan_steps_tilt,
                tracking_duration=self.tracking_duration,
            )

            if not pet_detected:
                logger.info("No pet detected during scan")
                self.camera_tracker.reset_position()
                return

            # Step 2: Capture images
            logger.info("Step 2: Capturing images...")
            file_paths = self.camera_tracker.capture_images(
                save_dir=self.save_dir,
                count=self.capture_count,
                long_edge=self.long_edge,
                jpeg_quality=self.jpeg_quality,
            )

            if not file_paths:
                logger.warning("No images captured")
                return

            logger.info(f"Captured {len(file_paths)} images")

            # Step 3: Upload to Slack
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

            # Reset camera position
            self.camera_tracker.reset_position()
            logger.info("Monitoring cycle completed successfully")

        except Exception as e:
            logger.error(f"Error during monitoring cycle: {e}", exc_info=True)
            try:
                self.camera_tracker.reset_position()
            except Exception as reset_error:
                logger.error(f"Failed to reset camera position: {reset_error}")

    def test_system(self):
        """Test system components."""
        logger.info("Testing system components...")

        # Test Slack connection
        logger.info("Testing Slack connection...")
        if self.slack_uploader.test_connection():
            logger.info("✓ Slack connection OK")
        else:
            logger.error("✗ Slack connection failed")
            return False

        # Test camera
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

        # Test servos
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
        """Run the monitoring system with scheduled execution."""
        logger.info("Pet Monitoring System starting...")

        # Test system before starting
        if not self.test_system():
            logger.error("System test failed. Exiting...")
            sys.exit(1)

        # Schedule the monitoring cycle
        schedule.every(self.schedule_interval).minutes.do(self.run_monitoring_cycle)

        # Run immediately on startup
        self.run_monitoring_cycle()

        # Main loop
        logger.info(f"Entering main loop (checking every {self.schedule_interval} minutes)")
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            self.cleanup()

    def cleanup(self):
        """Cleanup system resources."""
        logger.info("Cleaning up resources...")
        try:
            self.camera_tracker.cleanup()
            logger.info("Cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


def main():
    """Main entry point."""
    try:
        system = PetMonitoringSystem()
        system.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()