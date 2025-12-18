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
import csv
from datetime import datetime
from typing import Optional, Tuple, List
import cv2
import numpy as np
from picamera2 import Picamera2
from raspi_hailo8l_yolo import YOLODetector, is_hailo_available
import servo_control


class CameraTracker:
    """Pan-Tilt camera tracker with YOLOv8 pet detection."""

    def __init__(
        self,
        model_path: str = "models/yolov8s_h8l.hef",
        frame_width: int = 640,
        frame_height: int = 480,
        pan_channel: int = 0,
        tilt_channel: int = 1,
        kp_pan: float = 0.01,
        kp_tilt: float = 0.01,
        deadband: Optional[int] = 40,
        delta_angle_max: float = 1.0,
        target_classes: Optional[List[str]] = None,
        flip_vertical: bool = False,
        log_file: Optional[str] = None,
    ):
        """
        カメラトラッカーの初期化

        Args:
            model_path: Hailo-8L用YOLOv8モデルファイルのパス（HEF形式）
            frame_width: カメラ画像の幅
            frame_height: カメラ画像の高さ
            pan_channel: PCA9685のパン（水平）サーボチャンネル番号
            tilt_channel: PCA9685のチルト（垂直）サーボチャンネル番号
            kp_pan: パン制御の比例ゲイン（P制御パラメータ）
            kp_tilt: チルト制御の比例ゲイン（P制御パラメータ）
            deadband: 微小な揺れを防ぐための不感帯（ピクセル単位、Noneの場合は画面幅の4%を使用）
            delta_angle_max: 1回の更新での最大角度変化量（度）
            target_classes: 検出対象のクラス名リスト（例: ['person'], ['cat', 'dog']）
                           Noneの場合はデフォルトで['cat', 'dog']を使用
            flip_vertical: カメラ映像を上下反転するか（カメラを逆さまに設置した場合）
            log_file: デバッグログのCSVファイルパス（Noneの場合はログ出力なし）
        """
        # 検出対象クラスの設定（デフォルトは犬・猫）
        if target_classes is None:
            target_classes = ['cat', 'dog']

        # Hailo-8L用YOLO検出器の初期化
        self.detector = YOLODetector(model_path, target_classes=target_classes)

        # カメラの設定（Picamera2を使用）
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.flip_vertical = flip_vertical  # 上下反転フラグ
        self.picam2 = None  # Picamera2オブジェクト（後で初期化）

        # サーボ制御の初期化
        # servo_control.pyライブラリを使用してサーボを初期化
        self.kit = servo_control.initialize_servo_kit()

        # チャンネル番号を保存（servo_control.pyの定数と一致することを確認）
        self.pan_channel = pan_channel
        self.tilt_channel = tilt_channel

        # P制御のパラメータ設定
        self.kp_pan = kp_pan  # パンの比例ゲイン（大きいほど反応が速い）
        self.kp_tilt = kp_tilt  # チルトの比例ゲイン

        # デッドバンドの設定（未指定の場合は画面幅の4%を使用）
        if deadband is None:
            self.deadband = int(0.04 * frame_width)
        else:
            self.deadband = deadband

        # 角度変化量の上限（急峻な動きを防止してサーボ振動を抑える）
        self.delta_angle_max = delta_angle_max

        # サーボを中央位置に初期化
        # servo_control.pyの仕様: パン80度、チルト90度
        self.pan_angle = servo_control.PAN_CENTER
        self.tilt_angle = servo_control.TILT_CENTER
        servo_control.set_center_position(self.kit)
        time.sleep(0.5)  # サーボが位置に到達するまで待機

        # デバッグログの初期化
        self.log_file = log_file
        self._csv_writer = None
        self._log_file_handle = None
        if log_file:
            self._init_log_file()

    def _init_log_file(self):
        """デバッグログファイルの初期化（CSVヘッダー書き込み）"""
        self._log_file_handle = open(self.log_file, 'w', newline='', encoding='utf-8')
        self._csv_writer = csv.writer(self._log_file_handle)
        # CSVヘッダー
        self._csv_writer.writerow([
            'timestamp',
            'bbox_cx', 'bbox_cy',       # バウンディングボックス中心座標
            'frame_cx', 'frame_cy',     # 画面中心座標
            'error_x', 'error_y',       # 誤差（ピクセル）
            'deadband',                 # デッドバンド値
            'in_deadband_x', 'in_deadband_y',  # デッドバンド内か
            'raw_delta_pan', 'raw_delta_tilt', # 制限前の角度変化量
            'delta_pan', 'delta_tilt',  # 制限後の角度変化量
            'pan_angle', 'tilt_angle',  # サーボ指令角度
        ])
        self._log_file_handle.flush()
        print(f"ログファイル作成: {self.log_file}")

    def _log_tracking_data(self, cx: int, cy: int, error_x: float, error_y: float,
                           raw_delta_pan: float, raw_delta_tilt: float,
                           delta_pan: float, delta_tilt: float):
        """追跡データをログに記録"""
        if self._csv_writer is None:
            return

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        frame_cx = self.frame_width / 2
        frame_cy = self.frame_height / 2
        in_deadband_x = abs(error_x) <= self.deadband
        in_deadband_y = abs(error_y) <= self.deadband

        self._csv_writer.writerow([
            timestamp,
            cx, cy,
            frame_cx, frame_cy,
            f'{error_x:.1f}', f'{error_y:.1f}',
            self.deadband,
            in_deadband_x, in_deadband_y,
            f'{raw_delta_pan:.3f}', f'{raw_delta_tilt:.3f}',
            f'{delta_pan:.3f}', f'{delta_tilt:.3f}',
            f'{self.pan_angle:.1f}', f'{self.tilt_angle:.1f}',
        ])
        self._log_file_handle.flush()

    def _close_log_file(self):
        """ログファイルを閉じる"""
        if self._log_file_handle:
            self._log_file_handle.close()
            self._log_file_handle = None
            self._csv_writer = None

    def _open_camera(self) -> bool:
        """
        Picamera2でカメラデバイスを開く

        Returns:
            True: カメラが正常に開けた場合
            False: カメラを開けなかった場合
        """
        # 既にカメラが開いている場合はそのまま使用
        if self.picam2 is not None:
            return True

        try:
            # Picamera2オブジェクトを作成
            self.picam2 = Picamera2()

            # ビデオ設定（連続フレーム取得用、BGR形式で出力）
            config = self.picam2.create_video_configuration(
                main={"size": (self.frame_width, self.frame_height), "format": "BGR888"}
            )
            self.picam2.configure(config)
            self.picam2.start()

            # カメラの安定化を待機
            time.sleep(0.5)
            return True
        except Exception as e:
            print(f"Failed to open camera: {e}")
            self.picam2 = None
            return False

    def _close_camera(self):
        """Picamera2カメラを停止して閉じる"""
        if self.picam2 is not None:
            self.picam2.stop()
            self.picam2.close()
            self.picam2 = None

    def _capture_frame(self) -> np.ndarray:
        """
        カメラからフレームを取得（上下反転オプション対応）

        Returns:
            np.ndarray: BGR形式のフレーム画像
        """
        frame = self.picam2.capture_array()
        # 上下反転処理（カメラの取り付け向きに対応）
        if self.flip_vertical:
            frame = cv2.flip(frame, 0)  # 0: 上下反転
        return frame

    def _detect_pet(self, frame: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """
        Hailo-8LのYOLOv8を使用してフレーム内のペット（犬または猫）を検出

        Args:
            frame: 入力画像（BGR形式のnumpy配列）

        Returns:
            検出された場合: バウンディングボックス (x1, y1, x2, y2)
            検出されなかった場合: None
        """
        # Hailo-8L検出器で物体検出を実行（犬・猫のみフィルタリング済み）
        detections = self.detector.detect(frame)

        # 最も信頼度の高いペット検出を探す
        best_box = None
        best_conf = 0.0  # 最高信頼度

        for det in detections:
            conf = det['confidence']  # 信頼度

            # 最高信頼度を更新する場合
            if conf > best_conf:
                best_conf = conf
                # バウンディングボックスの座標を取得
                bbox = det['bbox']  # [x1, y1, x2, y2]
                best_box = (int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3]))

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

    def _update_servo_angles(self, cx: int, cy: int, error_x: float, error_y: float):
        """
        P制御（比例制御）を使用してサーボ角度を更新

        P制御: 誤差に比例した制御量を出力するシンプルな制御方式
        制御量 = Kp × 誤差

        さらに角度変化量の上限を設けることで、急峻な動きを防止し
        サーボ内部制御との干渉やオーバーシュートを抑える。

        Args:
            cx: バウンディングボックス中心X座標（ログ用）
            cy: バウンディングボックス中心Y座標（ログ用）
            error_x: 水平方向の誤差（ピクセル単位）
            error_y: 垂直方向の誤差（ピクセル単位）
        """
        # P制御による角度変化量を計算
        # パン: 対象が右(error_x>0)→パン角度を増やす(右を向く)
        # パンは左右方向なのでflipの影響を受けない
        raw_delta_pan = self.kp_pan * error_x

        # チルト: カメラの取り付け向きで制御方向が変わる
        # 通常マウント:
        #   TILT_UP(135°) = カメラが上を向く
        #   対象が上(error_y<0) → チルト増加 → 上を向く
        # 逆さまマウント(flip):
        #   TILT_UP(135°) = カメラが下を向く（カメラ本体が逆さまのため）
        #   TILT_DOWN(45°) = カメラが上を向く
        #   対象が上(error_y<0) → チルト減少 → 上を向く
        if self.flip_vertical:
            # 逆さまマウント: 符号を反転
            raw_delta_tilt = self.kp_tilt * error_y
        else:
            # 通常マウント
            raw_delta_tilt = -self.kp_tilt * error_y

        # 実際に適用する角度変化量（デッドバンド・制限適用後）
        delta_pan = 0.0
        delta_tilt = 0.0

        # 不感帯を適用して微小な揺れを防止
        # 誤差が不感帯より大きい場合のみサーボを動かす
        if abs(error_x) > self.deadband:
            # 角度変化量の制限（急峻な動きを防止）
            delta_pan = max(-self.delta_angle_max, min(self.delta_angle_max, raw_delta_pan))

            # 角度を更新（servo_control.pyの動作範囲: 35〜125度）
            new_pan_angle = self.pan_angle + delta_pan
            new_pan_angle = max(servo_control.PAN_LEFT,
                              min(servo_control.PAN_RIGHT, new_pan_angle))

            # servo_control.pyを使用して角度を設定
            try:
                servo_control.set_pan_angle(self.kit, new_pan_angle)
                self.pan_angle = new_pan_angle
            except ValueError as e:
                # 範囲外エラーの場合はログ出力（実際は範囲制限済みなので発生しない）
                print(f"Pan angle error: {e}")

        if abs(error_y) > self.deadband:
            # 角度変化量の制限（急峻な動きを防止）
            delta_tilt = max(-self.delta_angle_max, min(self.delta_angle_max, raw_delta_tilt))

            # 角度を更新（servo_control.pyの動作範囲: 45〜135度）
            new_tilt_angle = self.tilt_angle + delta_tilt
            new_tilt_angle = max(servo_control.TILT_DOWN,
                                min(servo_control.TILT_UP, new_tilt_angle))

            # servo_control.pyを使用して角度を設定
            try:
                servo_control.set_tilt_angle(self.kit, new_tilt_angle)
                self.tilt_angle = new_tilt_angle
            except ValueError as e:
                # 範囲外エラーの場合はログ出力（実際は範囲制限済みなので発生しない）
                print(f"Tilt angle error: {e}")

        # デバッグログに記録
        self._log_tracking_data(cx, cy, error_x, error_y,
                                raw_delta_pan, raw_delta_tilt,
                                delta_pan, delta_tilt)

    def scan_and_track(
        self,
        scan_steps_pan: int = 9,
        scan_steps_tilt: int = 5,
        tracking_duration: float = 8.0,
        tracking_fps: float = 10.0,
        show_display: bool = False,
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
            show_display: カメラ映像をウィンドウに表示するかどうか

        Returns:
            True: ペットを検出して追跡した場合
            False: ペットが見つからなかった場合
            None: ユーザがqキーで終了した場合
        """
        if not self._open_camera():
            raise RuntimeError("Failed to open camera")

        try:
            # ========== スキャンフェーズ ==========
            print("Starting scan...")
            detected = False

            # チルト（上下）を段階的に変更
            # servo_control.pyの動作範囲: 45〜135度
            for tilt_angle in np.linspace(servo_control.TILT_DOWN,
                                         servo_control.TILT_UP,
                                         scan_steps_tilt):
                self.tilt_angle = tilt_angle
                servo_control.set_tilt_angle(self.kit, tilt_angle, smooth=False)
                time.sleep(0.3)  # サーボが安定するまで待機

                # パン（左右）を段階的に変更
                # servo_control.pyの動作範囲: 35〜125度
                for pan_angle in np.linspace(servo_control.PAN_LEFT,
                                            servo_control.PAN_RIGHT,
                                            scan_steps_pan):
                    self.pan_angle = pan_angle
                    servo_control.set_pan_angle(self.kit, pan_angle, smooth=False)
                    time.sleep(0.2)  # サーボが安定するまで待機

                    # フレームを取得して検出を実行
                    frame = self._capture_frame()

                    box = self._detect_pet(frame)

                    # 画面表示（オプション）
                    if show_display:
                        display_frame = frame.copy()
                        if box is not None:
                            # 検出枠を描画
                            cv2.rectangle(display_frame, (box[0], box[1]), (box[2], box[3]), (0, 255, 0), 2)
                        # スキャン位置を表示
                        cv2.putText(display_frame, f"Scan: pan={pan_angle:.0f} tilt={tilt_angle:.0f}",
                                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                        cv2.imshow("Camera Tracker", display_frame)
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            print("終了キーが押されました")
                            return None  # ユーザ終了

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
                frame = self._capture_frame()

                # ペットを検出
                box = self._detect_pet(frame)
                if box is not None:
                    # バウンディングボックスの中心座標を取得
                    cx, cy = self._get_box_center(box)
                    # 画面中央との誤差を計算
                    error_x = cx - self.frame_width / 2
                    error_y = cy - self.frame_height / 2
                    # サーボ角度を更新して追従（ログ記録も実行）
                    self._update_servo_angles(cx, cy, error_x, error_y)

                # 画面表示（オプション）
                if show_display:
                    display_frame = frame.copy()
                    # 画面中央に十字線を描画
                    center_x, center_y = self.frame_width // 2, self.frame_height // 2
                    cv2.line(display_frame, (center_x - 20, center_y), (center_x + 20, center_y), (255, 255, 0), 1)
                    cv2.line(display_frame, (center_x, center_y - 20), (center_x, center_y + 20), (255, 255, 0), 1)

                    if box is not None:
                        # 検出枠を描画
                        cv2.rectangle(display_frame, (box[0], box[1]), (box[2], box[3]), (0, 255, 0), 2)
                        # 検出中心点を描画
                        cv2.circle(display_frame, (cx, cy), 5, (0, 0, 255), -1)
                    # 追跡情報を表示
                    remaining = tracking_duration - (time.time() - start_time)
                    cv2.putText(display_frame, f"Tracking: {remaining:.1f}s pan={self.pan_angle:.0f} tilt={self.tilt_angle:.0f}",
                                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.imshow("Camera Tracker", display_frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        print("終了キーが押されました")
                        return None  # ユーザ終了

                # ループのタイミングを維持（指定FPSを保つ）
                elapsed = time.time() - loop_start
                if elapsed < frame_delay:
                    time.sleep(frame_delay - elapsed)

            print("Tracking completed")
            return True

        finally:
            self._close_camera()
            if show_display:
                cv2.destroyAllWindows()

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
                frame = self._capture_frame()

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
        """サーボを中央位置にリセット（パン80度、チルト90度）"""
        self.pan_angle = servo_control.PAN_CENTER
        self.tilt_angle = servo_control.TILT_CENTER
        servo_control.set_center_position(self.kit)

    def cleanup(self):
        """リソースのクリーンアップ（カメラを閉じてサーボをリセット、ログを閉じる）"""
        self._close_camera()
        self._close_log_file()
        self.reset_position()


# ============================================================================
# CLIアプリケーション
# ============================================================================
def main():
    """
    メイン関数：コマンドライン引数を処理してカメラトラッカーを実行
    スキャン→検出→追跡の一連の処理を実行します。
    """
    import argparse
    from raspi_hailo8l_yolo import COCO_CLASSES

    parser = argparse.ArgumentParser(
        description="Pan-Tilt Camera Tracker with YOLOv8 (Hailo-8L)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # モデル設定
    parser.add_argument('--model', type=str,
                        default='models/yolov8s_h8l.hef',
                        help='HEFモデルファイルのパス')

    # 検出対象クラス
    parser.add_argument('--classes', type=str, nargs='+',
                        default=None,
                        help='検出対象のクラス名（スペース区切り、例: --classes person cat dog）')

    parser.add_argument('--list-classes', action='store_true',
                        help='使用可能なクラス名の一覧を表示して終了')

    # カメラ設定
    parser.add_argument('--width', type=int, default=640,
                        help='カメラ画像の幅')

    parser.add_argument('--height', type=int, default=480,
                        help='カメラ画像の高さ')

    parser.add_argument('--flip', action='store_true',
                        help='カメラ映像を上下反転（カメラを逆さまに設置した場合）')

    # P制御パラメータ
    parser.add_argument('--kp-pan', type=float, default=0.01,
                        help='パン制御の比例ゲイン')

    parser.add_argument('--kp-tilt', type=float, default=0.01,
                        help='チルト制御の比例ゲイン')

    parser.add_argument('--deadband', type=int, default=40,
                        help='不感帯（ピクセル）')

    parser.add_argument('--delta-max', type=float, default=1.0,
                        help='1回の更新での最大角度変化量（度）')

    # スキャン・追跡設定
    parser.add_argument('--scan-pan', type=int, default=9,
                        help='パン軸のスキャンステップ数')

    parser.add_argument('--scan-tilt', type=int, default=5,
                        help='チルト軸のスキャンステップ数')

    parser.add_argument('--duration', type=float, default=8.0,
                        help='追跡時間（秒）、--continuousと併用時は無視')

    parser.add_argument('--fps', type=float, default=5.0,
                        help='追跡ループの更新頻度（Hz）')

    parser.add_argument('--continuous', action='store_true',
                        help='ユーザが停止するまで継続実行（Ctrl+Cまたはqキーで終了）')

    # 表示設定
    parser.add_argument('--display', action='store_true',
                        help='カメラ映像をウィンドウに表示する（qキーで終了）')

    # ログ設定
    parser.add_argument('--log', type=str, default=None,
                        help='デバッグログのCSVファイルパス（例: --log tracking.csv）')

    # 画像キャプチャ設定
    parser.add_argument('--capture', action='store_true',
                        help='追跡後に画像をキャプチャする')

    parser.add_argument('--capture-dir', type=str, default='captures',
                        help='キャプチャ画像の保存先ディレクトリ')

    parser.add_argument('--capture-count', type=int, default=3,
                        help='キャプチャする画像の枚数')

    args = parser.parse_args()

    # クラス一覧表示モード
    if args.list_classes:
        print("使用可能なクラス名（COCO 80クラス）:")
        print("-" * 50)
        for i, name in enumerate(COCO_CLASSES):
            print(f"  {i:2d}: {name}")
        print("-" * 50)
        print(f"合計: {len(COCO_CLASSES)} クラス")
        print("\n使用例: --classes person cat dog")
        return

    # 設定表示
    print("=== Pan-Tilt Camera Tracker ===")
    print(f"モデル: {args.model}")
    print(f"解像度: {args.width}x{args.height}")
    if args.classes:
        print(f"検出対象: {', '.join(args.classes)}")
    else:
        print("検出対象: cat, dog（デフォルト）")
    print(f"P制御ゲイン: pan={args.kp_pan}, tilt={args.kp_tilt}")
    print(f"最大角度変化: {args.delta_max}度/更新")
    if args.continuous:
        print("実行モード: 継続実行（Ctrl+C または qキーで終了）")
    else:
        print(f"追跡時間: {args.duration}秒")
    if args.flip:
        print("カメラ映像: 上下反転")
    if args.display:
        print("表示: ON")
    if args.log:
        print(f"ログ出力: {args.log}")
    print()

    tracker = None

    try:
        # CameraTrackerの初期化
        tracker = CameraTracker(
            model_path=args.model,
            frame_width=args.width,
            frame_height=args.height,
            kp_pan=args.kp_pan,
            kp_tilt=args.kp_tilt,
            deadband=args.deadband,
            delta_angle_max=args.delta_max,
            target_classes=args.classes,
            flip_vertical=args.flip,
            log_file=args.log,
        )

        # 継続実行モードの場合は無限ループ
        if args.continuous:
            print("継続実行モード開始...")
            while True:
                result = tracker.scan_and_track(
                    scan_steps_pan=args.scan_pan,
                    scan_steps_tilt=args.scan_tilt,
                    tracking_duration=float('inf'),  # 無限追跡
                    tracking_fps=args.fps,
                    show_display=args.display,
                )
                # ユーザがqキーで終了した場合
                if result is None:
                    print("ユーザにより終了されました")
                    break
                # 対象が見つからなかった場合は再スキャン
                if not result:
                    print("対象が見つかりません。再スキャン...")
                    time.sleep(1.0)
        else:
            # 通常モード：指定時間だけ追跡
            found = tracker.scan_and_track(
                scan_steps_pan=args.scan_pan,
                scan_steps_tilt=args.scan_tilt,
                tracking_duration=args.duration,
                tracking_fps=args.fps,
                show_display=args.display,
            )

            if found:
                print("対象を検出・追跡しました")

                # 画像キャプチャ（オプション）
                if args.capture:
                    print(f"画像をキャプチャ中...")
                    paths = tracker.capture_images(
                        save_dir=args.capture_dir,
                        count=args.capture_count,
                    )
                    print(f"保存完了: {len(paths)}枚")
                    for p in paths:
                        print(f"  - {p}")
            else:
                print("対象が見つかりませんでした")

    except KeyboardInterrupt:
        print("\n中断されました")

    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if tracker:
            tracker.cleanup()
            print("クリーンアップ完了")


if __name__ == "__main__":
    main()