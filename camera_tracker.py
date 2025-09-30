"""
Camera Tracker Module for Pet Monitoring System

This module handles:
- Pan/Tilt servo initialization
- Full area scanning
- P-control tracking
- Still image capture (3 images with resizing and JPEG compression)
"""

import time
import os
from datetime import datetime
from typing import Optional, Tuple, List
import cv2
import numpy as np
from ultralytics import YOLO
import busio
import board
from adafruit_servokit import ServoKit


class CameraTracker:
    """Pan-Tilt camera tracker with YOLOv8 pet detection."""

    def __init__(
        self,
        model_path: str = "yolov8n.pt",
        camera_index: int = 0,
        frame_width: int = 640,
        frame_height: int = 480,
        pan_channel: int = 0,
        tilt_channel: int = 1,
        kp_pan: float = 0.02,
        kp_tilt: float = 0.02,
        deadband: int = 10,
    ):
        """
        Initialize camera tracker.

        Args:
            model_path: Path to YOLOv8 model file
            camera_index: Camera device index
            frame_width: Camera frame width
            frame_height: Camera frame height
            pan_channel: PCA9685 channel for pan servo
            tilt_channel: PCA9685 channel for tilt servo
            kp_pan: Proportional gain for pan control
            kp_tilt: Proportional gain for tilt control
            deadband: Deadband in pixels to prevent micro-jitter
        """
        # Initialize YOLO model
        self.model = YOLO(model_path)

        # Camera settings
        self.camera_index = camera_index
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.cap = None

        # Initialize servo control
        i2c = busio.I2C(board.SCL, board.SDA)
        self.kit = ServoKit(channels=16, i2c=i2c)
        self.pan_servo = self.kit.servo[pan_channel]
        self.tilt_servo = self.kit.servo[tilt_channel]

        # P-control parameters
        self.kp_pan = kp_pan
        self.kp_tilt = kp_tilt
        self.deadband = deadband

        # Target classes (dog and cat in COCO dataset)
        self.target_classes = [15, 16]  # 15: cat, 16: dog

        # Initialize servo positions to center
        self.pan_angle = 90
        self.tilt_angle = 90
        self.pan_servo.angle = self.pan_angle
        self.tilt_servo.angle = self.tilt_angle
        time.sleep(0.5)  # Wait for servos to reach position

    def _open_camera(self) -> bool:
        """
        Open camera device.

        Returns:
            True if camera opened successfully, False otherwise
        """
        if self.cap is not None and self.cap.isOpened():
            return True

        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            return False

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
        return True

    def _close_camera(self):
        """Close camera device."""
        if self.cap is not None and self.cap.isOpened():
            self.cap.release()
            self.cap = None

    def _detect_pet(self, frame: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """
        Detect pet (dog or cat) in frame using YOLOv8.

        Args:
            frame: Input frame (BGR format)

        Returns:
            Bounding box (x1, y1, x2, y2) if pet detected, None otherwise
        """
        results = self.model(frame, verbose=False)

        # Find highest confidence pet detection
        best_box = None
        best_conf = 0.0

        for result in results:
            boxes = result.boxes
            for box in boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])

                if cls in self.target_classes and conf > best_conf:
                    best_conf = conf
                    xyxy = box.xyxy[0].cpu().numpy()
                    best_box = (int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3]))

        return best_box

    def _get_box_center(self, box: Tuple[int, int, int, int]) -> Tuple[int, int]:
        """
        Get center coordinates of bounding box.

        Args:
            box: Bounding box (x1, y1, x2, y2)

        Returns:
            Center coordinates (cx, cy)
        """
        x1, y1, x2, y2 = box
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        return cx, cy

    def _update_servo_angles(self, error_x: float, error_y: float):
        """
        Update servo angles using P-control.

        Args:
            error_x: Horizontal error in pixels (target - center)
            error_y: Vertical error in pixels (target - center)
        """
        # Apply deadband to prevent micro-jitter
        if abs(error_x) > self.deadband:
            delta_pan = -self.kp_pan * error_x
            self.pan_angle = max(0, min(180, self.pan_angle + delta_pan))
            self.pan_servo.angle = self.pan_angle

        if abs(error_y) > self.deadband:
            delta_tilt = self.kp_tilt * error_y
            self.tilt_angle = max(0, min(180, self.tilt_angle + delta_tilt))
            self.tilt_servo.angle = self.tilt_angle

    def scan_and_track(
        self,
        scan_steps_pan: int = 9,
        scan_steps_tilt: int = 5,
        tracking_duration: float = 8.0,
        tracking_fps: float = 10.0,
    ) -> bool:
        """
        Scan full range of motion to detect pet, then track if found.

        Args:
            scan_steps_pan: Number of steps for pan axis scan
            scan_steps_tilt: Number of steps for tilt axis scan
            tracking_duration: Duration to track in seconds
            tracking_fps: Tracking loop frequency in Hz

        Returns:
            True if pet detected and tracked, False otherwise
        """
        if not self._open_camera():
            raise RuntimeError("Failed to open camera")

        try:
            # Scan phase
            print("Starting scan...")
            detected = False

            for tilt_angle in np.linspace(30, 150, scan_steps_tilt):
                self.tilt_angle = tilt_angle
                self.tilt_servo.angle = tilt_angle
                time.sleep(0.3)  # Wait for servo to settle

                for pan_angle in np.linspace(0, 180, scan_steps_pan):
                    self.pan_angle = pan_angle
                    self.pan_servo.angle = pan_angle
                    time.sleep(0.2)

                    # Capture frame and detect
                    ret, frame = self.cap.read()
                    if not ret:
                        continue

                    box = self._detect_pet(frame)
                    if box is not None:
                        print(f"Pet detected at pan={pan_angle:.1f}, tilt={tilt_angle:.1f}")
                        detected = True
                        break

                if detected:
                    break

            if not detected:
                print("No pet detected during scan")
                return False

            # Tracking phase
            print(f"Starting tracking for {tracking_duration} seconds...")
            start_time = time.time()
            frame_delay = 1.0 / tracking_fps

            while time.time() - start_time < tracking_duration:
                loop_start = time.time()

                ret, frame = self.cap.read()
                if not ret:
                    break

                box = self._detect_pet(frame)
                if box is not None:
                    cx, cy = self._get_box_center(box)
                    error_x = cx - self.frame_width / 2
                    error_y = cy - self.frame_height / 2
                    self._update_servo_angles(error_x, error_y)

                # Maintain loop timing
                elapsed = time.time() - loop_start
                if elapsed < frame_delay:
                    time.sleep(frame_delay - elapsed)

            print("Tracking completed")
            return True

        finally:
            self._close_camera()

    def capture_images(
        self,
        save_dir: str,
        count: int = 3,
        long_edge: int = 800,
        jpeg_quality: int = 70,
        interval: float = 0.5,
    ) -> List[str]:
        """
        Capture still images with resizing and JPEG compression.

        Args:
            save_dir: Directory to save images
            count: Number of images to capture
            long_edge: Target size for long edge in pixels
            jpeg_quality: JPEG compression quality (0-100)
            interval: Interval between captures in seconds

        Returns:
            List of saved file paths
        """
        if not self._open_camera():
            raise RuntimeError("Failed to open camera")

        # Create save directory if it doesn't exist
        os.makedirs(save_dir, exist_ok=True)

        file_paths = []

        try:
            for i in range(count):
                if i > 0:
                    time.sleep(interval)

                ret, frame = self.cap.read()
                if not ret:
                    print(f"Failed to capture image {i+1}/{count}")
                    continue

                # Resize image
                height, width = frame.shape[:2]
                if width > height:
                    new_width = long_edge
                    new_height = int(height * long_edge / width)
                else:
                    new_height = long_edge
                    new_width = int(width * long_edge / height)

                resized = cv2.resize(frame, (new_width, new_height))

                # Generate filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                filename = f"pet_{timestamp}_{i+1}.jpg"
                filepath = os.path.join(save_dir, filename)

                # Save with JPEG compression
                cv2.imwrite(filepath, resized, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
                file_paths.append(filepath)
                print(f"Saved: {filepath}")

        finally:
            self._close_camera()

        return file_paths

    def reset_position(self):
        """Reset servos to center position."""
        self.pan_angle = 90
        self.tilt_angle = 90
        self.pan_servo.angle = self.pan_angle
        self.tilt_servo.angle = self.tilt_angle

    def cleanup(self):
        """Cleanup resources."""
        self._close_camera()
        self.reset_position()