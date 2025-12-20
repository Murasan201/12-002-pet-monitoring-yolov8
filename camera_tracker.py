#!/usr/bin/env python3
"""
カメラトラッカーモジュール

Hailo-8L + YOLOv8によるペット検出とP制御によるカメラ追跡を提供する。
検出したペットを画角中央に捉え続け、バウンディングボックス付き画像を保存する。

Usage:
    # ライブラリとして使用
    from camera_tracker import scan_and_track, capture_images, get_latest_image

    # CLIとして使用
    python camera_tracker.py
    python camera_tracker.py --display --continuous

要件定義書: docs/pet_monitoring_requirements.md
詳細仕様: docs/detection_and_tracking_specification.md
"""

import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any

import cv2
import numpy as np
from dotenv import load_dotenv

# 既存モジュールをインポート
from raspi_hailo8l_yolo import YOLODetector, CameraManager, draw_detections
import servo_control


# 環境変数を.envファイルから読み込む
load_dotenv()

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==================== グローバル変数（モジュールレベルのシングルトン） ====================
# 最新の保存画像パスを記録（複数モジュール間で共有）
_latest_image_path: Optional[str] = None
_tracker_instance: Optional['CameraTracker'] = None


# ==================== 公開API関数 ====================

def scan_and_track(
    scan_steps_pan: int = 9,
    scan_steps_tilt: int = 5,
    tracking_duration: float = 8.0,
    tracking_fps: float = 5.0,
    continuous: bool = False
) -> dict:
    """
    可動域全体をスキャンし、ペット検出時に追跡へ移行する。

    スキャンパターンで可動域を探索し、ペット（犬・猫）を発見すると
    P制御による追跡モードに切り替わる。追跡中はペットを画角中央に
    捉え続ける。

    Args:
        scan_steps_pan: パン軸のスキャンステップ数（デフォルト: 9）
        scan_steps_tilt: チルト軸のスキャンステップ数（デフォルト: 5）
        tracking_duration: 追跡時間（秒）（デフォルト: 8.0）
        tracking_fps: 追跡ループの更新頻度（Hz）（デフォルト: 5.0）
        continuous: 継続実行モード（デフォルト: False）

    Returns:
        dict: 実行結果
            {
                "detected": bool,      # ペットを検出したか
                "tracked": bool,       # 追跡を実行したか
                "error": str | None    # エラーメッセージ
            }

    Example:
        >>> result = scan_and_track()
        >>> if result["detected"]:
        ...     print("ペットを検出して追跡しました")
    """
    global _tracker_instance

    try:
        # トラッカーインスタンスの初期化（シングルトン）
        if _tracker_instance is None:
            _tracker_instance = _create_tracker_from_env()

        # スキャン→追跡実行
        detected = _tracker_instance.scan_and_track(
            scan_steps_pan=scan_steps_pan,
            scan_steps_tilt=scan_steps_tilt,
            tracking_duration=tracking_duration,
            tracking_fps=tracking_fps,
            continuous=continuous
        )

        return {
            "detected": detected,
            "tracked": detected,
            "error": None
        }

    except Exception as e:
        logger.error(f"スキャン・追跡に失敗しました: {e}")
        return {
            "detected": False,
            "tracked": False,
            "error": str(e)
        }


def capture_images(
    count: int = 3,
    long_edge: int = 800,
    jpeg_quality: int = 70
) -> list[str]:
    """
    画像を撮影・保存し、ファイルパス配列を返す。

    バウンディングボックス付きの画像を指定枚数撮影し、
    JPEG圧縮・リサイズして保存する。Slack通知用の画像生成を想定。

    Args:
        count: 撮影枚数（デフォルト: 3）
        long_edge: 画像長辺サイズ（ピクセル）（デフォルト: 800）
        jpeg_quality: JPEG品質（0-100）（デフォルト: 70）

    Returns:
        list[str]: 保存したファイルパスのリスト

    Raises:
        RuntimeError: カメラが開けない場合

    Example:
        >>> paths = capture_images(count=3, long_edge=800)
        >>> print(f"{len(paths)}枚の画像を保存しました")
    """
    global _tracker_instance

    try:
        # トラッカーインスタンスの初期化（シングルトン）
        if _tracker_instance is None:
            _tracker_instance = _create_tracker_from_env()

        # 環境変数から保存ディレクトリを取得
        save_dir = os.getenv("IMAGE_SAVE_DIR", "./captured_images")

        # 画像キャプチャ実行
        file_paths = _tracker_instance.capture_images(
            save_dir=save_dir,
            count=count,
            long_edge=long_edge,
            jpeg_quality=jpeg_quality
        )

        return file_paths

    except Exception as e:
        logger.error(f"画像キャプチャに失敗しました: {e}")
        return []


def get_latest_image() -> str | None:
    """
    最新の保存済み画像パスを返す。

    capture_images()で保存された最新の画像ファイルパスを返す。
    一度も画像が保存されていない場合はNoneを返す。

    Returns:
        str | None: 最新画像のファイルパス、または None

    Example:
        >>> latest = get_latest_image()
        >>> if latest:
        ...     print(f"最新画像: {latest}")
    """
    return _latest_image_path


def cleanup():
    """
    リソースのクリーンアップを実行する。

    カメラ、サーボ、その他のリソースを解放する。
    プログラム終了時に必ず呼び出すこと。
    """
    global _tracker_instance

    if _tracker_instance is not None:
        _tracker_instance.cleanup()
        _tracker_instance = None


# ==================== 内部ヘルパー関数 ====================

def _create_tracker_from_env() -> 'CameraTracker':
    """
    環境変数からCameraTrackerインスタンスを生成する。

    Returns:
        CameraTracker: 初期化済みトラッカーインスタンス
    """
    # 環境変数からパラメータを取得
    model_path = os.getenv("YOLO_MODEL_PATH", "models/yolov8s_h8l.hef")
    camera_index = int(os.getenv("CAMERA_INDEX", "0"))
    frame_width = int(os.getenv("FRAME_WIDTH", "640"))
    frame_height = int(os.getenv("FRAME_HEIGHT", "480"))
    flip_vertical = os.getenv("CAMERA_FLIP_VERTICAL", "true").lower() == "true"

    # P制御パラメータ（実機検証済みデフォルト値）
    kp_pan = float(os.getenv("KP_PAN", "0.01"))
    kp_tilt = float(os.getenv("KP_TILT", "0.01"))
    deadband = int(os.getenv("DEADBAND", "40"))

    logger.info("CameraTrackerを初期化中...")
    logger.info(f"  モデル: {model_path}")
    logger.info(f"  カメラ: index={camera_index}, {frame_width}x{frame_height}")
    logger.info(f"  上下反転: {flip_vertical}")
    logger.info(f"  P制御: Kp_pan={kp_pan}, Kp_tilt={kp_tilt}, deadband={deadband}px")

    return CameraTracker(
        model_path=model_path,
        camera_index=camera_index,
        frame_width=frame_width,
        frame_height=frame_height,
        flip_vertical=flip_vertical,
        kp_pan=kp_pan,
        kp_tilt=kp_tilt,
        deadband=deadband
    )


# ==================== CameraTrackerクラス ====================

class CameraTracker:
    """
    カメラ追跡クラス

    YOLOv8による物体検出とP制御によるサーボ追跡を統合したクラス。
    スキャン、追跡、画像キャプチャの全機能を提供する。

    設計意図:
        - Hailo-8Lライブラリ（raspi_hailo8l_yolo）を使用した高速検出
        - サーボ制御ライブラリ（servo_control）による滑らかな動作
        - P制御による中央追従（デッドバンド機構で微小振動防止）
        - 画像保存機能によるSlack通知連携

    Attributes:
        detector: YOLODetectorインスタンス
        camera: CameraManagerインスタンス
        servo_kit: ServoKitインスタンス
        current_pan_angle: 現在のパン角度
        current_tilt_angle: 現在のチルト角度
    """

    def __init__(
        self,
        model_path: str = "models/yolov8s_h8l.hef",
        camera_index: int = 0,
        frame_width: int = 640,
        frame_height: int = 480,
        flip_vertical: bool = False,
        target_classes: Optional[List[str]] = None,
        kp_pan: float = 0.01,
        kp_tilt: float = 0.01,
        deadband: int = 40,
        delta_angle_max: float = 1.0
    ):
        """
        CameraTrackerの初期化

        Args:
            model_path: YOLOv8 Hailo-8Lモデルファイルのパス
            camera_index: カメラデバイスのインデックス
            frame_width: フレーム幅（ピクセル）
            frame_height: フレーム高さ（ピクセル）
            flip_vertical: カメラ上下反転フラグ
            target_classes: 検出対象クラス名（Noneで犬・猫のみ）
            kp_pan: パンのP制御ゲイン（実機検証済み: 0.01）
            kp_tilt: チルトのP制御ゲイン（実機検証済み: 0.01）
            deadband: デッドバンド幅（ピクセル）（実機検証済み: 40px）
            delta_angle_max: 1回の更新での最大角度変化量（度）（実機検証済み: 1.0°）
        """
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.kp_pan = kp_pan
        self.kp_tilt = kp_tilt
        self.deadband = deadband
        self.delta_angle_max = delta_angle_max

        # 検出対象クラスのデフォルト設定（犬・猫）
        if target_classes is None:
            target_classes = ['cat', 'dog']

        # YOLODetectorの初期化（Hailo-8L使用）
        logger.info(f"YOLODetector初期化中（モデル: {model_path}）...")
        self.detector = YOLODetector(
            model_path=model_path,
            target_classes=target_classes
        )
        logger.info(f"  検出対象: {target_classes}")

        # CameraManagerの初期化
        logger.info(f"カメラ初期化中（{frame_width}x{frame_height}）...")
        self.camera = CameraManager(
            resolution=(frame_width, frame_height),
            device_id=camera_index,
            flip_vertical=flip_vertical
        )

        # サーボ制御の初期化
        logger.info("サーボ初期化中...")
        self.servo_kit = servo_control.initialize_servo_kit()

        # サーボ角度の初期化（中央位置）
        self.current_pan_angle = servo_control.PAN_CENTER
        self.current_tilt_angle = servo_control.TILT_CENTER
        servo_control.set_center_position(self.servo_kit)

        logger.info("CameraTracker初期化完了")

    def scan_and_track(
        self,
        scan_steps_pan: int = 9,
        scan_steps_tilt: int = 5,
        tracking_duration: float = 8.0,
        tracking_fps: float = 5.0,
        continuous: bool = False,
        display: bool = False,
        log_csv: Optional[str] = None
    ) -> bool:
        """
        全域スキャンを実施し、ペット検出時に追跡へ移行する。

        可動域全体をステップ走査してペットを探し、発見したら
        P制御による追跡モードに移行する。追跡中はペットを画角中央に
        捉え続ける。

        Args:
            scan_steps_pan: パン軸のスキャンステップ数
            scan_steps_tilt: チルト軸のスキャンステップ数
            tracking_duration: 追跡時間（秒）
            tracking_fps: 追跡ループの更新頻度（Hz）
            continuous: 継続実行モード（True時は永続ループ）
            display: 映像表示フラグ（True時はウィンドウ表示）
            log_csv: デバッグログCSVファイルパス（Noneでログ無効）

        Returns:
            bool: ペット検出・追跡成功時はTrue
        """
        detected = False

        try:
            if continuous:
                logger.info("継続実行モード開始（Ctrl+C または qキーで終了）")
                while True:
                    # スキャン実施
                    box = self._scan_area(scan_steps_pan, scan_steps_tilt, display)

                    if box is not None:
                        logger.info("ペット検出！追跡モードへ移行します")
                        # 追跡実施
                        self._track_pet(
                            duration=tracking_duration,
                            fps=tracking_fps,
                            display=display,
                            log_csv=log_csv
                        )
                        detected = True
                    else:
                        logger.info("ペットが見つかりませんでした。再スキャンします...")

                    time.sleep(1.0)

            else:
                # 単発実行モード
                logger.info("スキャン開始...")
                box = self._scan_area(scan_steps_pan, scan_steps_tilt, display)

                if box is not None:
                    logger.info("ペット検出！追跡モードへ移行します")
                    # 追跡実施
                    self._track_pet(
                        duration=tracking_duration,
                        fps=tracking_fps,
                        display=display,
                        log_csv=log_csv
                    )
                    detected = True
                else:
                    logger.info("ペットが見つかりませんでした")

        except KeyboardInterrupt:
            logger.info("ユーザーによる中断")

        return detected

    def _scan_area(
        self,
        steps_pan: int,
        steps_tilt: int,
        display: bool = False
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        可動域全体をスキャンしてペットを探索する。

        チルト角を段階的に変更し、各チルト位置でパンを左右にスキャンする。
        ペット検出時はその位置で停止し、バウンディングボックスを返す。

        Args:
            steps_pan: パン軸のステップ数
            steps_tilt: チルト軸のステップ数
            display: 映像表示フラグ

        Returns:
            Optional[Tuple]: 検出時はバウンディングボックス (x1, y1, x2, y2)、
                            未検出時はNone
        """
        # スキャン範囲の計算
        pan_range = servo_control.PAN_RIGHT - servo_control.PAN_LEFT
        tilt_range = servo_control.TILT_UP - servo_control.TILT_DOWN

        pan_step = pan_range / (steps_pan - 1) if steps_pan > 1 else 0
        tilt_step = tilt_range / (steps_tilt - 1) if steps_tilt > 1 else 0

        logger.info(f"スキャン範囲: パン {servo_control.PAN_LEFT}-{servo_control.PAN_RIGHT}度、チルト {servo_control.TILT_DOWN}-{servo_control.TILT_UP}度")
        logger.info(f"ステップ数: パン {steps_pan}、チルト {steps_tilt}")

        # チルト軸をスキャン
        for i in range(steps_tilt):
            tilt_angle = servo_control.TILT_DOWN + i * tilt_step
            servo_control.set_tilt_angle(self.servo_kit, tilt_angle)
            self.current_tilt_angle = tilt_angle
            time.sleep(0.3)  # チルト移動後の安定待機

            # パン軸をスキャン
            for j in range(steps_pan):
                pan_angle = servo_control.PAN_LEFT + j * pan_step
                servo_control.set_pan_angle(self.servo_kit, pan_angle)
                self.current_pan_angle = pan_angle
                time.sleep(0.2)  # パン移動後の安定待機

                # フレーム取得
                frame = self.camera.read_frame()
                if frame is None:
                    continue

                # ペット検出
                box = self._detect_pet(frame)

                # 映像表示（displayフラグがTrueの場合）
                if display:
                    self._display_frame(frame, box)

                if box is not None:
                    logger.info(f"ペット検出（パン: {pan_angle:.1f}度、チルト: {tilt_angle:.1f}度）")
                    return box

        return None

    def _track_pet(
        self,
        duration: float,
        fps: float,
        display: bool = False,
        log_csv: Optional[str] = None
    ):
        """
        ペットをP制御で追跡する。

        検出したペットの位置を基準に、P制御で画角中央に捉え続ける。
        デッドバンド機構により微小振動を防止する。

        Args:
            duration: 追跡時間（秒）
            fps: 追跡ループの更新頻度（Hz）
            display: 映像表示フラグ
            log_csv: デバッグログCSVファイルパス
        """
        logger.info(f"追跡開始（時間: {duration}秒、FPS: {fps} Hz）")

        start_time = time.time()
        frame_delay = 1.0 / fps

        # CSVログの初期化
        csv_file = None
        if log_csv:
            csv_file = open(log_csv, 'w', newline='', encoding='utf-8')
            csv_file.write("timestamp,error_x,error_y,delta_pan,delta_tilt,pan_angle,tilt_angle\n")

        try:
            while time.time() - start_time < duration:
                loop_start = time.time()

                # フレーム取得
                frame = self.camera.read_frame()
                if frame is None:
                    continue

                # ペット検出
                box = self._detect_pet(frame)

                if box is not None:
                    # バウンディングボックスの中心座標を計算
                    x1, y1, x2, y2 = box
                    cx = (x1 + x2) // 2
                    cy = (y1 + y2) // 2

                    # 画面中央との誤差を計算
                    center_x = self.frame_width / 2
                    center_y = self.frame_height / 2
                    error_x = cx - center_x
                    error_y = cy - center_y

                    # P制御で角度変化量を計算（デッドバンド適用）
                    delta_pan, delta_tilt = self._calculate_control(error_x, error_y)

                    # サーボ角度を更新
                    self._update_servo_angles(delta_pan, delta_tilt)

                    # CSVログに記録
                    if csv_file:
                        csv_file.write(f"{time.time()},{error_x},{error_y},{delta_pan},{delta_tilt},{self.current_pan_angle},{self.current_tilt_angle}\n")

                # 映像表示
                if display:
                    self._display_frame(frame, box)

                # フレームレート維持
                elapsed = time.time() - loop_start
                if elapsed < frame_delay:
                    time.sleep(frame_delay - elapsed)

        finally:
            if csv_file:
                csv_file.close()

        logger.info("追跡終了")

    def _detect_pet(self, frame: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """
        フレームからペット（犬・猫）を検出する。

        YOLOv8でフレームを解析し、信頼度が最も高いペットの
        バウンディングボックスを返す。複数検出された場合は
        最も信頼度の高い1体のみを追跡対象とする。

        Args:
            frame: 入力フレーム（BGR形式）

        Returns:
            Optional[Tuple]: 検出時はバウンディングボックス (x1, y1, x2, y2)、
                            未検出時はNone
        """
        # Hailo-8L検出器で物体検出を実行（target_classesで犬・猫のみフィルタリング済み）
        detections = self.detector.detect(frame)

        if not detections:
            return None

        # 最も信頼度の高い検出を選択
        best_box = None
        best_conf = 0.0

        for det in detections:
            conf = det['confidence']
            if conf > best_conf:
                best_conf = conf
                bbox = det['bbox']  # [x1, y1, x2, y2]
                best_box = (int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3]))

        return best_box

    def _calculate_control(
        self,
        error_x: float,
        error_y: float
    ) -> Tuple[float, float]:
        """
        P制御で角度変化量を計算する。

        画面中央とペット位置の誤差から、P制御式に基づいて
        サーボの角度変化量を計算する。デッドバンド機構により
        微小な誤差は無視される。

        Args:
            error_x: X方向の誤差（ピクセル）
            error_y: Y方向の誤差（ピクセル）

        Returns:
            Tuple[float, float]: (delta_pan, delta_tilt) 角度変化量（度）
        """
        delta_pan = 0.0
        delta_tilt = 0.0

        # デッドバンド適用（X方向）
        if abs(error_x) > self.deadband:
            # P制御式: 制御量 = -Kp × 誤差
            # マイナス符号はサーボ座標系の向きを調整するため
            delta_pan = -self.kp_pan * error_x

            # 角度変化量の制限（急峻な動作を防止）
            delta_pan = max(-self.delta_angle_max, min(self.delta_angle_max, delta_pan))

        # デッドバンド適用（Y方向）
        if abs(error_y) > self.deadband:
            # P制御式: 制御量 = Kp × 誤差
            delta_tilt = self.kp_tilt * error_y

            # 角度変化量の制限
            delta_tilt = max(-self.delta_angle_max, min(self.delta_angle_max, delta_tilt))

        return delta_pan, delta_tilt

    def _update_servo_angles(self, delta_pan: float, delta_tilt: float):
        """
        サーボ角度を更新する。

        計算された角度変化量を現在角度に加算し、
        サーボの可動範囲内にクリップしてから指令を送る。

        Args:
            delta_pan: パンの角度変化量（度）
            delta_tilt: チルトの角度変化量（度）
        """
        # 新しい角度を計算
        new_pan_angle = self.current_pan_angle + delta_pan
        new_tilt_angle = self.current_tilt_angle + delta_tilt

        # 角度範囲にクリップ
        new_pan_angle = max(servo_control.PAN_LEFT, min(servo_control.PAN_RIGHT, new_pan_angle))
        new_tilt_angle = max(servo_control.TILT_DOWN, min(servo_control.TILT_UP, new_tilt_angle))

        # サーボに指令（smoothパラメータをFalseにして直接移動）
        # P制御で既に滑らかな軌道が生成されているため、
        # サーボ側の台形制御は不要
        servo_control.set_pan_angle(self.servo_kit, new_pan_angle, smooth=False)
        servo_control.set_tilt_angle(self.servo_kit, new_tilt_angle, smooth=False)

        # 現在角度を更新
        self.current_pan_angle = new_pan_angle
        self.current_tilt_angle = new_tilt_angle

    def _display_frame(self, frame: np.ndarray, box: Optional[Tuple[int, int, int, int]]):
        """
        フレームをウィンドウに表示する。

        バウンディングボックスと中心マーカーを描画してから表示する。
        qキーで表示を終了できる。

        Args:
            frame: 表示するフレーム
            box: バウンディングボックス（Noneの場合は枠なし）
        """
        display_frame = frame.copy()

        # バウンディングボックスの描画
        if box is not None:
            x1, y1, x2, y2 = box
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # 中心点の描画
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            cv2.circle(display_frame, (cx, cy), 5, (0, 255, 0), -1)

        # 画面中央のマーカー描画
        center_x = self.frame_width // 2
        center_y = self.frame_height // 2
        cv2.drawMarker(display_frame, (center_x, center_y), (0, 0, 255),
                      cv2.MARKER_CROSS, 20, 2)

        # デッドバンド領域の表示
        cv2.rectangle(
            display_frame,
            (center_x - self.deadband, center_y - self.deadband),
            (center_x + self.deadband, center_y + self.deadband),
            (255, 0, 0), 1
        )

        cv2.imshow('Camera Tracker', display_frame)
        cv2.waitKey(1)

    def capture_images(
        self,
        save_dir: str,
        count: int = 3,
        long_edge: int = 800,
        jpeg_quality: int = 70,
        interval: float = 0.5
    ) -> List[str]:
        """
        静止画を撮影してリサイズ・圧縮保存する。

        追跡完了後にペット画像を記録する。画像はSlack通知用に
        リサイズ・JPEG圧縮され、バウンディングボックス付きで保存される。

        Args:
            save_dir: 保存先ディレクトリ
            count: 撮影枚数
            long_edge: リサイズ後の長辺サイズ（ピクセル）
            jpeg_quality: JPEG圧縮品質（0-100）
            interval: 撮影間隔（秒）

        Returns:
            List[str]: 保存したファイルパスのリスト

        Raises:
            RuntimeError: カメラが開けない場合
        """
        global _latest_image_path

        # 保存ディレクトリの作成
        save_path = Path(save_dir)
        save_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"画像キャプチャ開始（{count}枚、長辺{long_edge}px、品質{jpeg_quality}）")

        file_paths = []

        for i in range(count):
            # フレーム取得
            frame = self.camera.read_frame()
            if frame is None:
                logger.warning(f"フレーム取得失敗（{i+1}/{count}枚目）")
                continue

            # ペット検出（バウンディングボックス描画用）
            detections = self.detector.detect(frame)
            if detections:
                # バウンディングボックスを描画
                frame = draw_detections(frame, detections)

            # 画像リサイズ（アスペクト比維持）
            frame = self._resize_image(frame, long_edge)

            # ファイル名生成（タイムスタンプ付き）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # ミリ秒まで
            filename = f"pet_{timestamp}_{i+1}.jpg"
            file_path = save_path / filename

            # JPEG保存
            cv2.imwrite(
                str(file_path),
                frame,
                [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality]
            )

            file_paths.append(str(file_path))
            logger.info(f"  保存: {file_path}")

            # 最新画像パスを更新
            _latest_image_path = str(file_path)

            # 撮影間隔待機
            if i < count - 1:
                time.sleep(interval)

        logger.info(f"画像キャプチャ完了（{len(file_paths)}枚）")
        return file_paths

    def _resize_image(self, image: np.ndarray, long_edge: int) -> np.ndarray:
        """
        画像をアスペクト比を維持してリサイズする。

        長辺を指定サイズに合わせてリサイズする。
        ファイルサイズ削減とSlack通知の転送効率化を目的とする。

        Args:
            image: 入力画像
            long_edge: リサイズ後の長辺サイズ（ピクセル）

        Returns:
            np.ndarray: リサイズ後の画像
        """
        height, width = image.shape[:2]

        # アスペクト比を維持してリサイズサイズを計算
        if width > height:
            # 横長画像
            new_width = long_edge
            new_height = int(height * long_edge / width)
        else:
            # 縦長画像
            new_height = long_edge
            new_width = int(width * long_edge / height)

        # リサイズ実行
        resized = cv2.resize(image, (new_width, new_height))
        return resized

    def reset_position(self):
        """
        サーボを中央位置にリセットする。

        パン・チルトサーボを中央位置（PAN_CENTER, TILT_CENTER）に移動する。
        スキャン開始前やシステム終了時に使用する。
        """
        logger.info("サーボを中央位置にリセット中...")
        servo_control.set_center_position(self.servo_kit)
        self.current_pan_angle = servo_control.PAN_CENTER
        self.current_tilt_angle = servo_control.TILT_CENTER
        logger.info("リセット完了")

    def cleanup(self):
        """
        リソースのクリーンアップを実行する。

        カメラ解放、サーボリセット、OpenCVウィンドウ破棄を行う。
        プログラム終了時に必ず呼び出すこと。
        """
        logger.info("リソースをクリーンアップ中...")

        # カメラ解放
        if hasattr(self, 'camera'):
            self.camera.release()

        # サーボを中央位置に戻して解放
        if hasattr(self, 'servo_kit'):
            try:
                servo_control.set_center_position(self.servo_kit)
                servo_control.release_servos(self.servo_kit)
            except Exception as e:
                logger.warning(f"サーボ解放エラー: {e}")

        # OpenCVウィンドウ破棄
        cv2.destroyAllWindows()

        logger.info("クリーンアップ完了")


# ==================== CLIモード ====================

def main():
    """
    CLIモードのメイン処理。

    コマンドライン引数を解析してカメラトラッカーを実行する。
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="カメラトラッカー - Hailo-8L + YOLOv8によるペット追跡システム",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 基本的な実行（デフォルト設定：犬・猫を検出、8秒追跡）
  python camera_tracker.py

  # 映像を表示しながら継続実行
  python camera_tracker.py --display --continuous

  # P制御パラメータを調整
  python camera_tracker.py --kp-pan 0.02 --kp-tilt 0.02 --deadband 20

  # デバッグログを出力
  python camera_tracker.py --log tracking.csv --display

  # 追跡後に画像をキャプチャ
  python camera_tracker.py --capture --capture-dir ./images --capture-count 5

  # 使用可能なクラス一覧を表示
  python camera_tracker.py --list-classes
        """
    )

    # 基本パラメータ
    parser.add_argument('--model', type=str, default='models/yolov8s_h8l.hef',
                       help='HEFモデルファイルのパス')
    parser.add_argument('--classes', type=str, nargs='+', default=['cat', 'dog'],
                       help='検出対象のクラス名（スペース区切り）')
    parser.add_argument('--list-classes', action='store_true',
                       help='使用可能なクラス名一覧を表示して終了')

    # カメラパラメータ
    parser.add_argument('--width', type=int, default=640,
                       help='カメラ画像の幅（ピクセル）')
    parser.add_argument('--height', type=int, default=480,
                       help='カメラ画像の高さ（ピクセル）')
    parser.add_argument('--flip', action='store_true',
                       help='カメラ映像を上下反転（逆さま設置時）')

    # P制御パラメータ
    parser.add_argument('--kp-pan', type=float, default=0.01,
                       help='パン制御の比例ゲイン')
    parser.add_argument('--kp-tilt', type=float, default=0.01,
                       help='チルト制御の比例ゲイン')
    parser.add_argument('--deadband', type=int, default=40,
                       help='不感帯（ピクセル）')
    parser.add_argument('--delta-max', type=float, default=1.0,
                       help='1回の更新での最大角度変化量（度）')

    # スキャン・追跡パラメータ
    parser.add_argument('--scan-pan', type=int, default=9,
                       help='パン軸のスキャンステップ数')
    parser.add_argument('--scan-tilt', type=int, default=5,
                       help='チルト軸のスキャンステップ数')
    parser.add_argument('--duration', type=float, default=8.0,
                       help='追跡時間（秒）')
    parser.add_argument('--fps', type=float, default=5.0,
                       help='追跡ループの更新頻度（Hz）')
    parser.add_argument('--continuous', action='store_true',
                       help='継続実行モード（Ctrl+C または qキーで終了）')

    # 表示・ログパラメータ
    parser.add_argument('--display', action='store_true',
                       help='カメラ映像をウィンドウに表示')
    parser.add_argument('--log', type=str, default=None,
                       help='デバッグログのCSVファイルパス')

    # 画像キャプチャパラメータ
    parser.add_argument('--capture', action='store_true',
                       help='追跡後に画像をキャプチャする')
    parser.add_argument('--capture-dir', type=str, default='captures',
                       help='キャプチャ画像の保存先ディレクトリ')
    parser.add_argument('--capture-count', type=int, default=3,
                       help='キャプチャする画像の枚数')

    args = parser.parse_args()

    # クラス一覧表示モード
    if args.list_classes:
        from raspi_hailo8l_yolo import COCO_CLASSES
        print("使用可能なクラス名（COCO 80クラス）:")
        print("-" * 50)
        for i, name in enumerate(COCO_CLASSES):
            print(f"  {i:2d}: {name}")
        print("-" * 50)
        print(f"合計: {len(COCO_CLASSES)} クラス")
        print("\n使用例: --classes person cat dog")
        return 0

    tracker = None

    try:
        # トラッカー初期化
        logger.info("=== カメラトラッカー ===")
        logger.info(f"モデル: {args.model}")
        logger.info(f"検出対象: {args.classes}")
        logger.info(f"解像度: {args.width}x{args.height}")
        logger.info(f"P制御: Kp_pan={args.kp_pan}, Kp_tilt={args.kp_tilt}, deadband={args.deadband}px")

        tracker = CameraTracker(
            model_path=args.model,
            frame_width=args.width,
            frame_height=args.height,
            flip_vertical=args.flip,
            target_classes=args.classes,
            kp_pan=args.kp_pan,
            kp_tilt=args.kp_tilt,
            deadband=args.deadband,
            delta_angle_max=args.delta_max
        )

        # スキャン→追跡実行
        detected = tracker.scan_and_track(
            scan_steps_pan=args.scan_pan,
            scan_steps_tilt=args.scan_tilt,
            tracking_duration=args.duration,
            tracking_fps=args.fps,
            continuous=args.continuous,
            display=args.display,
            log_csv=args.log
        )

        # 画像キャプチャ（オプション）
        if detected and args.capture:
            logger.info("画像キャプチャを実行します...")
            file_paths = tracker.capture_images(
                save_dir=args.capture_dir,
                count=args.capture_count
            )
            logger.info(f"{len(file_paths)}枚の画像を保存しました")

        return 0

    except KeyboardInterrupt:
        logger.info("ユーザーによる中断")
        return 0

    except Exception as e:
        logger.error(f"エラーが発生しました: {e}", exc_info=True)
        return 1

    finally:
        if tracker:
            tracker.cleanup()


if __name__ == "__main__":
    sys.exit(main())
