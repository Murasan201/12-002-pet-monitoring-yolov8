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
        カメラトラッカーの初期化

        Args:
            model_path: YOLOv8モデルファイルのパス
            camera_index: カメラデバイスのインデックス番号
            frame_width: カメラ画像の幅
            frame_height: カメラ画像の高さ
            pan_channel: PCA9685のパン（水平）サーボチャンネル番号
            tilt_channel: PCA9685のチルト（垂直）サーボチャンネル番号
            kp_pan: パン制御の比例ゲイン（P制御パラメータ）
            kp_tilt: チルト制御の比例ゲイン（P制御パラメータ）
            deadband: 微小な揺れを防ぐための不感帯（ピクセル単位）
        """
        # YOLOv8モデルの初期化（物体検出AIモデル）
        self.model = YOLO(model_path)

        # カメラの設定
        self.camera_index = camera_index
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.cap = None  # カメラキャプチャオブジェクト（後で初期化）

        # サーボ制御の初期化
        # I2C通信でPCA9685サーボドライバと接続
        i2c = busio.I2C(board.SCL, board.SDA)
        self.kit = ServoKit(channels=16, i2c=i2c)  # 16チャンネルのサーボキット
        self.pan_servo = self.kit.servo[pan_channel]  # パン（左右）サーボ
        self.tilt_servo = self.kit.servo[tilt_channel]  # チルト（上下）サーボ

        # P制御のパラメータ設定
        self.kp_pan = kp_pan  # パンの比例ゲイン（大きいほど反応が速い）
        self.kp_tilt = kp_tilt  # チルトの比例ゲイン
        self.deadband = deadband  # 不感帯（この範囲内の誤差は無視）

        # 検出対象のクラス（COCOデータセットのクラスID）
        self.target_classes = [15, 16]  # 15: 猫、16: 犬

        # サーボを中央位置（90度）に初期化
        self.pan_angle = 90
        self.tilt_angle = 90
        self.pan_servo.angle = self.pan_angle
        self.tilt_servo.angle = self.tilt_angle
        time.sleep(0.5)  # サーボが位置に到達するまで待機

    def _open_camera(self) -> bool:
        """
        カメラデバイスを開く

        Returns:
            True: カメラが正常に開けた場合
            False: カメラを開けなかった場合
        """
        # 既にカメラが開いている場合はそのまま使用
        if self.cap is not None and self.cap.isOpened():
            return True

        # カメラデバイスを開く
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            return False

        # カメラの解像度を設定
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
        return True

    def _close_camera(self):
        """カメラデバイスを閉じる"""
        if self.cap is not None and self.cap.isOpened():
            self.cap.release()
            self.cap = None

    def _detect_pet(self, frame: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """
        YOLOv8を使用してフレーム内のペット（犬または猫）を検出

        Args:
            frame: 入力画像（BGR形式のnumpy配列）

        Returns:
            検出された場合: バウンディングボックス (x1, y1, x2, y2)
            検出されなかった場合: None
        """
        # YOLOv8で物体検出を実行
        results = self.model(frame, verbose=False)

        # 最も信頼度の高いペット検出を探す
        best_box = None
        best_conf = 0.0  # 最高信頼度

        for result in results:
            boxes = result.boxes
            for box in boxes:
                cls = int(box.cls[0])  # クラスID
                conf = float(box.conf[0])  # 信頼度

                # ターゲットクラス（犬・猫）で、かつ最高信頼度を更新する場合
                if cls in self.target_classes and conf > best_conf:
                    best_conf = conf
                    # バウンディングボックスの座標を取得
                    xyxy = box.xyxy[0].cpu().numpy()
                    best_box = (int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3]))

        return best_box

    def _get_box_center(self, box: Tuple[int, int, int, int]) -> Tuple[int, int]:
        """
        バウンディングボックスの中心座標を取得

        Args:
            box: バウンディングボックス (x1, y1, x2, y2)

        Returns:
            中心座標 (cx, cy)
        """
        x1, y1, x2, y2 = box
        cx = (x1 + x2) // 2  # 中心のX座標
        cy = (y1 + y2) // 2  # 中心のY座標
        return cx, cy

    def _update_servo_angles(self, error_x: float, error_y: float):
        """
        P制御（比例制御）を使用してサーボ角度を更新

        P制御: 誤差に比例した制御量を出力するシンプルな制御方式
        制御量 = Kp × 誤差

        Args:
            error_x: 水平方向の誤差（ピクセル単位）
            error_y: 垂直方向の誤差（ピクセル単位）
        """
        # 不感帯を適用して微小な揺れを防止
        # 誤差が不感帯より大きい場合のみサーボを動かす
        if abs(error_x) > self.deadband:
            # パンの制御量を計算（マイナスは座標系の向きを調整）
            delta_pan = -self.kp_pan * error_x
            # 角度を更新（0〜180度の範囲に制限）
            self.pan_angle = max(0, min(180, self.pan_angle + delta_pan))
            self.pan_servo.angle = self.pan_angle

        if abs(error_y) > self.deadband:
            # チルトの制御量を計算
            delta_tilt = self.kp_tilt * error_y
            # 角度を更新（0〜180度の範囲に制限）
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
        可動域全体をスキャンしてペットを検出し、検出した場合は追跡する

        処理フロー:
        1. スキャンフェーズ: カメラを動かしながら全域を探索
        2. 検出: ペットを発見したら次のフェーズへ
        3. 追跡フェーズ: 一定時間ペットを画面中央に追従

        Args:
            scan_steps_pan: パン軸のスキャンステップ数
            scan_steps_tilt: チルト軸のスキャンステップ数
            tracking_duration: 追跡する時間（秒）
            tracking_fps: 追跡ループの更新頻度（Hz）

        Returns:
            True: ペットを検出して追跡した場合
            False: ペットが見つからなかった場合
        """
        if not self._open_camera():
            raise RuntimeError("Failed to open camera")

        try:
            # ========== スキャンフェーズ ==========
            print("Starting scan...")
            detected = False

            # チルト（上下）を段階的に変更
            for tilt_angle in np.linspace(30, 150, scan_steps_tilt):
                self.tilt_angle = tilt_angle
                self.tilt_servo.angle = tilt_angle
                time.sleep(0.3)  # サーボが安定するまで待機

                # パン（左右）を段階的に変更
                for pan_angle in np.linspace(0, 180, scan_steps_pan):
                    self.pan_angle = pan_angle
                    self.pan_servo.angle = pan_angle
                    time.sleep(0.2)  # サーボが安定するまで待機

                    # フレームを取得して検出を実行
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

            # ========== 追跡フェーズ ==========
            print(f"Starting tracking for {tracking_duration} seconds...")
            start_time = time.time()
            frame_delay = 1.0 / tracking_fps  # フレーム間隔

            while time.time() - start_time < tracking_duration:
                loop_start = time.time()

                # フレームを取得
                ret, frame = self.cap.read()
                if not ret:
                    break

                # ペットを検出
                box = self._detect_pet(frame)
                if box is not None:
                    # バウンディングボックスの中心座標を取得
                    cx, cy = self._get_box_center(box)
                    # 画面中央との誤差を計算
                    error_x = cx - self.frame_width / 2
                    error_y = cy - self.frame_height / 2
                    # サーボ角度を更新して追従
                    self._update_servo_angles(error_x, error_y)

                # ループのタイミングを維持（指定FPSを保つ）
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
        静止画を撮影し、リサイズとJPEG圧縮を行う

        画像は長辺を指定サイズにリサイズし、JPEG圧縮でファイルサイズを削減

        Args:
            save_dir: 画像の保存先ディレクトリ
            count: 撮影する画像の枚数
            long_edge: 長辺の目標サイズ（ピクセル）
            jpeg_quality: JPEG圧縮品質（0〜100、高いほど高品質）
            interval: 撮影間隔（秒）

        Returns:
            保存したファイルパスのリスト
        """
        if not self._open_camera():
            raise RuntimeError("Failed to open camera")

        # 保存先ディレクトリが存在しない場合は作成
        os.makedirs(save_dir, exist_ok=True)

        file_paths = []

        try:
            for i in range(count):
                # 2枚目以降は指定間隔を空ける
                if i > 0:
                    time.sleep(interval)

                # フレームを取得
                ret, frame = self.cap.read()
                if not ret:
                    print(f"Failed to capture image {i+1}/{count}")
                    continue

                # ========== 画像のリサイズ ==========
                height, width = frame.shape[:2]
                # アスペクト比を維持しながら長辺を指定サイズに
                if width > height:
                    new_width = long_edge
                    new_height = int(height * long_edge / width)
                else:
                    new_height = long_edge
                    new_width = int(width * long_edge / height)

                resized = cv2.resize(frame, (new_width, new_height))

                # ========== ファイル名の生成 ==========
                # タイムスタンプを含む一意のファイル名を生成
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                filename = f"pet_{timestamp}_{i+1}.jpg"
                filepath = os.path.join(save_dir, filename)

                # ========== JPEG圧縮して保存 ==========
                cv2.imwrite(filepath, resized, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
                file_paths.append(filepath)
                print(f"Saved: {filepath}")

        finally:
            self._close_camera()

        return file_paths

    def reset_position(self):
        """サーボを中央位置（90度）にリセット"""
        self.pan_angle = 90
        self.tilt_angle = 90
        self.pan_servo.angle = self.pan_angle
        self.tilt_servo.angle = self.tilt_angle

    def cleanup(self):
        """リソースのクリーンアップ（カメラを閉じてサーボをリセット）"""
        self._close_camera()
        self.reset_position()