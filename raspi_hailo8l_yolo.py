#!/usr/bin/env python3
"""
Raspberry Pi 5 + Hailo-8L YOLO物体検出アプリケーション/ライブラリ
Hailo-8L AIアクセラレータを使用したリアルタイムYOLO物体検出システム
要件定義書: docs/11_002_raspi_hailo_8_l_yolo_detector.md

このモジュールは以下の2つの使用方法をサポートします：

1. ライブラリとして使用（別プロジェクトからインポート）:
    from raspi_hailo8l_yolo import YOLODetector, CameraManager, draw_detections

    detector = YOLODetector("models/yolov8s_h8l.hef")
    detections = detector.detect(image)
    result = draw_detections(image, detections)

2. CLIアプリケーションとして実行:
    python raspi_hailo8l_yolo.py --res 1280x720 --conf 0.25 --iou 0.45
    python raspi_hailo8l_yolo.py --res 1280x720 --save

機能:
- リアルタイムカメラ映像からのYOLO物体検出
- Hailo-8L AIアクセラレータを使用した高速推論
- バウンディングボックス、クラス名、信頼度の表示
- 動画保存、ログ出力機能
"""

import cv2
import numpy as np
import argparse
import time
import os
import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

# ============================================================================
# ライブラリ公開API定義
# ============================================================================
__all__ = [
    # クラス
    'YOLODetector',
    'CameraManager',
    'DetectionLogger',
    # ユーティリティ関数
    'draw_detections',
    'draw_info',
    'parse_resolution',
    # 可用性チェック関数
    'is_hailo_available',
    'is_picamera_available',
    # ロガー設定
    'setup_logging',
    'get_logger',
    # 定数
    'COCO_CLASSES',
]

# ============================================================================
# 定数定義
# ============================================================================
# COCO データセットのクラス名（80クラス）
# YOLODetectorのtarget_classesパラメータで使用可能
COCO_CLASSES = [
    'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck',
    'boat', 'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench',
    'bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra',
    'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee',
    'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove',
    'skateboard', 'surfboard', 'tennis racket', 'bottle', 'wine glass', 'cup',
    'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple', 'sandwich', 'orange',
    'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
    'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse',
    'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink',
    'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier',
    'toothbrush'
]

# ============================================================================
# ロギング設定
# ============================================================================
# モジュール専用ロガー（ライブラリ使用時は呼び出し側でハンドラを設定可能）
_logger = logging.getLogger(__name__)


def setup_logging(level: int = logging.INFO,
                  format_string: str = None) -> logging.Logger:
    """
    ロギングの設定を行います。
    CLIアプリケーションとして使用する場合や、ライブラリ使用時に
    ログ出力を有効化したい場合に呼び出します。

    Args:
        level (int): ログレベル（logging.DEBUG, logging.INFO等）
        format_string (str): ログフォーマット文字列（Noneの場合はデフォルト使用）

    Returns:
        logging.Logger: 設定済みのロガーインスタンス

    使用例:
        # 基本的な使用
        setup_logging()

        # デバッグレベルで詳細出力
        setup_logging(level=logging.DEBUG)
    """
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(format_string))

    _logger.addHandler(handler)
    _logger.setLevel(level)

    return _logger


def get_logger() -> logging.Logger:
    """
    モジュールのロガーインスタンスを取得します。
    ライブラリ使用時にログハンドラをカスタマイズする場合に使用します。

    Returns:
        logging.Logger: モジュールのロガーインスタンス

    使用例:
        logger = get_logger()
        logger.addHandler(my_custom_handler)
    """
    return _logger


# ============================================================================
# 依存ライブラリの遅延インポートと可用性チェック
# ============================================================================
# グローバルフラグ（インポート時に警告を出さない）
_PICAMERA2_AVAILABLE: Optional[bool] = None
_HAILO_AVAILABLE: Optional[bool] = None

# 遅延インポート用のモジュール参照
_Picamera2 = None
_hailo_platform = None
_HEF = None
_VDevice = None
_HailoStreamInterface = None
_InferVStreams = None
_ConfigureParams = None
_InputVStreamParams = None
_OutputVStreamParams = None
_FormatType = None


def _check_picamera2() -> bool:
    """Picamera2の可用性をチェックし、利用可能ならインポートする"""
    global _PICAMERA2_AVAILABLE, _Picamera2

    if _PICAMERA2_AVAILABLE is not None:
        return _PICAMERA2_AVAILABLE

    try:
        from picamera2 import Picamera2
        _Picamera2 = Picamera2
        _PICAMERA2_AVAILABLE = True
        _logger.debug("Picamera2 が利用可能です")
    except ImportError:
        _PICAMERA2_AVAILABLE = False
        _logger.debug("Picamera2 が利用できません。USB Webカメラモードで動作します。")

    return _PICAMERA2_AVAILABLE


def _check_hailo() -> bool:
    """HailoRT SDKの可用性をチェックし、利用可能ならインポートする"""
    global _HAILO_AVAILABLE
    global _hailo_platform, _HEF, _VDevice, _HailoStreamInterface
    global _InferVStreams, _ConfigureParams
    global _InputVStreamParams, _OutputVStreamParams, _FormatType

    if _HAILO_AVAILABLE is not None:
        return _HAILO_AVAILABLE

    try:
        import hailo_platform
        from hailo_platform import (HEF, VDevice, HailoStreamInterface,
                                   InferVStreams, ConfigureParams,
                                   InputVStreamParams, OutputVStreamParams,
                                   FormatType)
        _hailo_platform = hailo_platform
        _HEF = HEF
        _VDevice = VDevice
        _HailoStreamInterface = HailoStreamInterface
        _InferVStreams = InferVStreams
        _ConfigureParams = ConfigureParams
        _InputVStreamParams = InputVStreamParams
        _OutputVStreamParams = OutputVStreamParams
        _FormatType = FormatType
        _HAILO_AVAILABLE = True
        _logger.debug("HailoRT SDK が利用可能です")
    except ImportError:
        _HAILO_AVAILABLE = False
        _logger.debug("HailoRT SDK が利用できません。CPUモードで動作します。")

    return _HAILO_AVAILABLE


def is_hailo_available() -> bool:
    """
    HailoRT SDKが利用可能かどうかを確認します。

    Returns:
        bool: HailoRT SDKが利用可能な場合はTrue

    使用例:
        if is_hailo_available():
            detector = YOLODetector("model.hef")
        else:
            print("Hailoが利用できません")
    """
    return _check_hailo()


def is_picamera_available() -> bool:
    """
    Picamera2（Camera Module V3用）が利用可能かどうかを確認します。

    Returns:
        bool: Picamera2が利用可能な場合はTrue

    使用例:
        if is_picamera_available():
            camera = CameraManager(use_picamera=True)
        else:
            camera = CameraManager(use_picamera=False)
    """
    return _check_picamera2()


# ============================================================================
# メインクラス定義
# ============================================================================
class YOLODetector:
    """
    YOLO物体検出器クラス（Hailo-8L対応）

    Hailo-8L AIアクセラレータを使用したリアルタイム物体検出を実行します。
    初心者向けに設計され、前処理・推論・後処理が明確に分離されています。

    ライブラリとして使用する場合の例:
        from raspi_hailo8l_yolo import YOLODetector, COCO_CLASSES

        # 全クラス検出（デフォルト）
        detector = YOLODetector("models/yolov8s_h8l.hef")

        # 特定クラスのみ検出（人と車のみ）
        detector = YOLODetector(
            "models/yolov8s_h8l.hef",
            target_classes=['person', 'car']
        )

        # 画像から物体検出
        import cv2
        image = cv2.imread("test.jpg")
        detections = detector.detect(image)

        # 結果の処理
        for det in detections:
            print(f"{det['class_name']}: {det['confidence']:.2f}")

        # 検出対象クラスを動的に変更
        detector.set_target_classes(['dog', 'cat'])
    """

    def __init__(self, model_path: str, conf_threshold: float = 0.25,
                 iou_threshold: float = 0.45,
                 target_classes: Optional[List[str]] = None):
        """
        YOLODetectorの初期化

        Args:
            model_path (str): HEFモデルファイルのパス（例: 'models/yolov8s_h8l.hef'）
            conf_threshold (float): 信頼度閾値（0.0-1.0、デフォルト: 0.25）
            iou_threshold (float): IoU閾値（NMS用、デフォルト: 0.45）
            target_classes (Optional[List[str]]): 検出対象のクラス名リスト
                - None: 全クラスを検出（デフォルト）
                - ['person', 'car']: 指定したクラスのみ検出
                使用可能なクラス名は COCO_CLASSES を参照

        Raises:
            FileNotFoundError: モデルファイルが見つからない場合
            RuntimeError: Hailoデバイスの初期化に失敗した場合
            ValueError: 無効なクラス名が指定された場合
        """
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.device = None
        self.hef = None
        self.network_group = None
        self.input_vstreams_params = None
        self.output_vstreams_params = None
        self.input_name = None
        self.output_name = None
        self._initialized = False

        # COCO データセットのクラス名（80クラス）
        self.class_names = COCO_CLASSES.copy()

        # 検出対象クラスの設定
        self._target_class_ids: Optional[set] = None
        if target_classes is not None:
            self.set_target_classes(target_classes)

        self._initialize_hailo()

    @property
    def is_initialized(self) -> bool:
        """
        Hailoデバイスが正常に初期化されているかを確認します。

        Returns:
            bool: 初期化済みの場合はTrue
        """
        return self._initialized

    @property
    def target_classes(self) -> Optional[List[str]]:
        """
        現在の検出対象クラス名リストを取得します。

        Returns:
            Optional[List[str]]: 検出対象クラス名のリスト。
                Noneの場合は全クラスが対象。
        """
        if self._target_class_ids is None:
            return None
        return [self.class_names[i] for i in sorted(self._target_class_ids)]

    def set_target_classes(self, class_names: Optional[List[str]]) -> None:
        """
        検出対象のクラスを設定します。

        Args:
            class_names (Optional[List[str]]): 検出対象のクラス名リスト
                - None: 全クラスを検出（フィルタリング解除）
                - ['person', 'car']: 指定したクラスのみ検出

        Raises:
            ValueError: 無効なクラス名が指定された場合

        使用例:
            # 人と車のみ検出
            detector.set_target_classes(['person', 'car'])

            # 全クラス検出に戻す
            detector.set_target_classes(None)

            # 動物のみ検出
            detector.set_target_classes(['dog', 'cat', 'bird', 'horse'])
        """
        if class_names is None:
            self._target_class_ids = None
            _logger.info("全クラスを検出対象に設定しました")
            return

        # クラス名からIDへの変換と検証
        class_ids = set()
        invalid_classes = []

        for name in class_names:
            name_lower = name.lower().strip()
            try:
                # 大文字小文字を区別しない検索
                class_id = next(
                    i for i, n in enumerate(self.class_names)
                    if n.lower() == name_lower
                )
                class_ids.add(class_id)
            except StopIteration:
                invalid_classes.append(name)

        if invalid_classes:
            available = ', '.join(self.class_names[:10]) + '...'
            raise ValueError(
                f"無効なクラス名が指定されました: {invalid_classes}\n"
                f"使用可能なクラス名: {available}\n"
                f"全クラスは COCO_CLASSES を参照してください"
            )

        self._target_class_ids = class_ids
        _logger.info(f"検出対象クラスを設定しました: {class_names}")

    def get_available_classes(self) -> List[str]:
        """
        使用可能な全クラス名のリストを取得します。

        Returns:
            List[str]: COCOデータセットの80クラス名リスト

        使用例:
            classes = detector.get_available_classes()
            print(classes)  # ['person', 'bicycle', 'car', ...]
        """
        return self.class_names.copy()

    def is_class_targeted(self, class_name: str) -> bool:
        """
        指定したクラスが検出対象かどうかを確認します。

        Args:
            class_name (str): 確認するクラス名

        Returns:
            bool: 検出対象の場合True
        """
        if self._target_class_ids is None:
            return True

        try:
            class_id = self.class_names.index(class_name.lower().strip())
            return class_id in self._target_class_ids
        except ValueError:
            return False

    def _initialize_hailo(self) -> None:
        """
        Hailoデバイスとモデルの初期化
        HEFファイルを読み込んでHailo-8Lデバイスを設定します。
        新しいHailoRT API（v4.x）に対応しています。
        """
        if not _check_hailo():
            _logger.warning("HailoRT SDK が利用できません。CPUモードで動作します。")
            return

        if not os.path.exists(self.model_path):
            error_msg = f"モデルファイルが見つかりません: {self.model_path}"
            _logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        try:
            # Hailo デバイスの初期化
            self.device = _VDevice()

            # HEF（Hailo Execution Format）ファイルの読み込み
            self.hef = _HEF(self.model_path)

            # 入出力ストリーム情報の取得
            input_vstream_infos = self.hef.get_input_vstream_infos()
            output_vstream_infos = self.hef.get_output_vstream_infos()

            # 入出力名の保存（推論時に使用）
            self.input_name = input_vstream_infos[0].name
            self.output_name = output_vstream_infos[0].name

            _logger.info(f"入力レイヤー: {self.input_name}")
            _logger.info(f"出力レイヤー: {self.output_name}")

            # ネットワークグループの設定（モデルをHailoデバイスにロード）
            configure_params = _ConfigureParams.create_from_hef(
                hef=self.hef, interface=_HailoStreamInterface.PCIe)
            network_groups = self.device.configure(self.hef, configure_params)
            self.network_group = network_groups[0]

            # 入出力VStreamsパラメータの作成
            # 入力: UINT8形式（0-255の画像データ）
            # 出力: FLOAT32形式（NMS後処理済みの検出結果）
            self.input_vstreams_params = _InputVStreamParams.make(
                self.network_group, format_type=_FormatType.UINT8)
            self.output_vstreams_params = _OutputVStreamParams.make(
                self.network_group, format_type=_FormatType.FLOAT32)

            self._initialized = True
            _logger.info("Hailo-8L デバイスが正常に初期化されました。")

        except Exception as e:
            error_msg = f"Hailo デバイスの初期化に失敗しました: {e}"
            _logger.error(error_msg)
            _logger.error("対処方法: hailortcli fw-control identify でデバイスを確認")
            self.device = None
            raise RuntimeError(error_msg) from e

    def preprocess_image(self, image: np.ndarray,
                        target_size: Tuple[int, int] = (640, 640)
                        ) -> np.ndarray:
        """
        画像の前処理（リサイズ、RGB変換）

        Args:
            image (np.ndarray): 入力画像（BGRフォーマット、OpenCVから取得）
            target_size (Tuple[int, int]): 目標サイズ (width, height)、デフォルト: (640, 640)

        Returns:
            np.ndarray: 前処理済み画像（UINT8形式、shape: (1, 640, 640, 3)）
        """
        # リサイズ：入力画像をモデルの入力サイズに統一
        resized = cv2.resize(image, target_size)

        # RGB変換：OpenCVはBGR形式ですが、YOLOはRGB形式を期待
        rgb_image = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        # HailoRT v4.x では入力は UINT8 形式（0-255）のまま使用
        # 正規化はHailo内部で自動的に行われる
        preprocessed = rgb_image.astype(np.uint8)

        # バッチ次元の追加：Hailo推論APIはバッチ処理に対応しているため、
        # （バッチサイズ, 高さ, 幅, チャンネル）形式に変更
        preprocessed = np.expand_dims(preprocessed, axis=0)

        return preprocessed

    def postprocess_detections(self, outputs: List,
                              original_shape: Tuple[int, int],
                              input_shape: Tuple[int, int] = (640, 640)
                              ) -> List[Dict[str, Any]]:
        """
        推論結果の後処理（座標変換）

        HailoRT v4.x のNMS後処理済み出力に対応しています。
        出力形式: [batch][class_id] = np.ndarray(N, 5)
        各検出は [y1, x1, y2, x2, confidence] の形式です。
        座標は0-1の正規化値で返されるため、ピクセル座標に変換します。

        Args:
            outputs (List): モデルの出力（NMS後処理済み）
            original_shape (Tuple[int, int]): 元画像のサイズ (height, width)
            input_shape (Tuple[int, int]): 入力画像のサイズ (height, width)

        Returns:
            List[Dict[str, Any]]: 検出結果のリスト。各辞書は以下を含む:
                - 'bbox' (list): バウンディングボックス座標 [x1, y1, x2, y2]
                - 'confidence' (float): 信頼度スコア（0.0-1.0）
                - 'class_id' (int): クラスID
                - 'class_name' (str): クラス名
        """
        detections = []

        if not outputs or len(outputs) == 0:
            return detections

        # HailoRT v4.x NMS後処理済み出力の解析
        # outputs[0] はバッチの最初の結果（1フレーム分）
        # outputs[0][class_id] は各クラスの検出結果 (N, 5) 形式
        batch_output = outputs[0]

        # 元画像のサイズ
        orig_h, orig_w = original_shape

        # 各クラスの検出結果を処理
        for class_id, class_detections in enumerate(batch_output):
            # ターゲットクラスが設定されている場合、対象外のクラスはスキップ
            if self._target_class_ids is not None:
                if class_id not in self._target_class_ids:
                    continue

            if not isinstance(class_detections, np.ndarray):
                continue

            if class_detections.size == 0:
                continue

            # 各検出を処理
            for detection in class_detections:
                # HailoRT NMS出力形式: [y1, x1, y2, x2, confidence]
                # 座標は0-1の正規化値
                y1_norm, x1_norm, y2_norm, x2_norm, confidence = detection

                if confidence < self.conf_threshold:
                    continue

                # 正規化座標を元画像のピクセル座標に変換
                # 正規化値（0-1）を直接元画像サイズに乗算
                x1 = int(x1_norm * orig_w)
                y1 = int(y1_norm * orig_h)
                x2 = int(x2_norm * orig_w)
                y2 = int(y2_norm * orig_h)

                # 座標の境界チェック
                x1 = max(0, min(x1, orig_w - 1))
                y1 = max(0, min(y1, orig_h - 1))
                x2 = max(0, min(x2, orig_w))
                y2 = max(0, min(y2, orig_h))

                # 有効なバウンディングボックスのみ追加
                if x2 > x1 and y2 > y1:
                    detections.append({
                        'bbox': [x1, y1, x2, y2],
                        'confidence': float(confidence),
                        'class_id': int(class_id),
                        'class_name': (self.class_names[class_id]
                                     if class_id < len(self.class_names)
                                     else f'class_{class_id}')
                    })

        # NMS は Hailo 側で既に適用済みなので、ここでは不要
        # ただし、信頼度順にソートして返す
        detections.sort(key=lambda x: x['confidence'], reverse=True)

        return detections

    def _apply_nms(self, detections: List[Dict[str, Any]]
                   ) -> List[Dict[str, Any]]:
        """
        Non-Maximum Suppression（NMS）の適用

        Args:
            detections (List[Dict[str, Any]]): 検出結果のリスト

        Returns:
            List[Dict[str, Any]]: NMS適用後の検出結果
        """
        if not detections:
            return detections

        # OpenCVのNMSを使用
        boxes = [det['bbox'] for det in detections]
        scores = [det['confidence'] for det in detections]

        indices = cv2.dnn.NMSBoxes(boxes, scores, self.conf_threshold, self.iou_threshold)

        if len(indices) > 0:
            indices = indices.flatten()
            return [detections[i] for i in indices]
        else:
            return []

    def detect(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        画像から物体検出を実行

        Args:
            image (np.ndarray): 入力画像（BGRフォーマット、任意の解像度）

        Returns:
            List[Dict[str, Any]]: 検出結果のリスト。各辞書は以下を含む:
                - 'bbox' (list): バウンディングボックス座標 [x1, y1, x2, y2]
                - 'confidence' (float): 信頼度スコア（0.0-1.0）
                - 'class_id' (int): クラスID（0-79、COCOデータセット）
                - 'class_name' (str): クラス名（例: 'person', 'car'）

        使用例:
            detector = YOLODetector("models/yolov8s_h8l.hef")
            image = cv2.imread("test.jpg")
            detections = detector.detect(image)
            for det in detections:
                print(f"{det['class_name']}: {det['confidence']:.2f}")
        """
        if self.device is None or not _check_hailo():
            # Hailoが利用できない場合、CPUモードでのダミー検出（テスト用）
            return self._dummy_detect(image)

        try:
            # 前処理：画像をモデル入力形式に変換
            preprocessed = self.preprocess_image(image)

            # 推論実行：Hailo-8Lで高速推論を実行
            # HailoRT v4.x API を使用
            with self.network_group.activate():
                with _InferVStreams(self.network_group,
                                   self.input_vstreams_params,
                                   self.output_vstreams_params) as infer_pipeline:
                    # 入力データの設定
                    input_dict = {self.input_name: preprocessed}

                    # 推論実行
                    output_dict = infer_pipeline.infer(input_dict)

                    # 出力の取得（NMS後処理済みの結果）
                    outputs = output_dict[self.output_name]

            # 後処理：推論結果から物体情報を抽出
            detections = self.postprocess_detections(outputs, image.shape[:2])

            return detections

        except Exception as e:
            _logger.error(f"推論に失敗しました: {e}")
            _logger.debug("詳細:", exc_info=True)
            return []

    def _dummy_detect(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        CPUモード用のダミー検出（Hailo非利用時のテスト用）

        Args:
            image (np.ndarray): 入力画像

        Returns:
            List[Dict[str, Any]]: テスト用の仮想検出結果
        """
        # Hailo非利用時のテスト用仮想検出結果
        # 実運用ではCPUベースのYOLO推論を実装することを推奨
        _logger.warning("Hailoが利用できないため、ダミー検出を返します")
        height, width = image.shape[:2]
        return [
            {
                'bbox': [width // 4, height // 4, width * 3 // 4, height * 3 // 4],
                'confidence': 0.85,
                'class_id': 0,
                'class_name': 'person'
            }
        ]


class CameraManager:
    """
    カメラ管理クラス

    Camera Module V3またはUSB Webカメラの初期化と制御を行います。
    自動フォールバック機能により、Picamera2が利用できない場合はUSBカメラに切り替わります。

    ライブラリとして使用する場合の例:
        from raspi_hailo8l_yolo import CameraManager

        # Camera Module V3を使用
        camera = CameraManager(resolution=(1280, 720))

        # フレームを取得
        frame = camera.read_frame()

        # 使用後は必ず解放
        camera.release()
    """

    def __init__(self, resolution: Tuple[int, int] = (1280, 720),
                 device_id: int = 0, flip_vertical: bool = False,
                 use_picamera: Optional[bool] = None):
        """
        カメラマネージャーの初期化

        Args:
            resolution (Tuple[int, int]): カメラ解像度 (width, height)、デフォルト: (1280, 720)
            device_id (int): カメラデバイスID（USB Webカメラ用、デフォルト: 0）
            flip_vertical (bool): 画像を上下反転するかどうか（カメラを逆さまに設置した場合）
            use_picamera (Optional[bool]): Picamera2を強制使用するかどうか
                - None: 自動判定（Picamera2が利用可能なら使用）
                - True: Picamera2を強制使用（利用不可なら例外）
                - False: USB Webカメラを強制使用

        Raises:
            RuntimeError: カメラの初期化に失敗した場合
        """
        self.resolution = resolution
        self.device_id = device_id
        self.flip_vertical = flip_vertical
        self.camera = None
        self.cap = None

        # Picamera2の使用判定
        if use_picamera is None:
            self.use_picamera = _check_picamera2()
        elif use_picamera:
            if not _check_picamera2():
                raise RuntimeError("Picamera2が利用できません")
            self.use_picamera = True
        else:
            self.use_picamera = False

        self._initialize_camera()

    def _initialize_camera(self) -> None:
        """
        Picamera2（Camera Module V3）の初期化
        Picamera2が利用できない場合は、自動的にUSBカメラに切り替わります。
        """
        if self.use_picamera:
            try:
                self.camera = _Picamera2()

                # Picamera2の設定（RGB888フォーマット）
                camera_config = self.camera.create_still_configuration(
                    main={"size": self.resolution, "format": "RGB888"}
                )
                self.camera.configure(camera_config)
                self.camera.start()

                _logger.info(f"Camera Module V3 を使用します。解像度: {self.resolution}")

            except Exception as e:
                _logger.warning(f"Camera Module V3 の初期化に失敗しました: {e}")
                self.use_picamera = False
                self._initialize_webcam()
        else:
            self._initialize_webcam()

    def _initialize_webcam(self) -> None:
        """
        USB Webカメラの初期化
        OpenCVのVideoCapture APIを使用してカメラを初期化します。
        """
        try:
            self.cap = cv2.VideoCapture(self.device_id)

            if not self.cap.isOpened():
                raise RuntimeError(f"カメラデバイス {self.device_id} を開けません")

            # 解像度設定（リクエストベース。実際の解像度はカメラの対応状況に依存）
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])

            _logger.info(f"USB Webカメラを使用します。解像度: {self.resolution}")

        except Exception as e:
            error_msg = f"USB Webカメラの初期化に失敗しました: {e}"
            _logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def read_frame(self) -> Optional[np.ndarray]:
        """
        カメラからフレームを読み取る

        Returns:
            Optional[np.ndarray]: フレーム画像（BGRフォーマット、shape: (height, width, 3)）
                読み取り失敗時はNoneを返す。flip_vertical=Trueの場合は上下反転済み。
        """
        try:
            frame = None

            if self.use_picamera and self.camera:
                # Picamera2からフレーム取得（RGB形式）
                frame = self.camera.capture_array()
                # RGB -> BGR 変換（OpenCVはBGR形式を使用）
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            elif self.cap:
                # USB Webカメラからフレーム取得
                ret, frame = self.cap.read()
                if not ret:
                    return None

            # 上下反転処理（カメラの取り付け向きに対応）
            if frame is not None and self.flip_vertical:
                frame = cv2.flip(frame, 0)  # 0: 上下反転

            return frame

        except Exception as e:
            _logger.error(f"フレーム読み取りに失敗しました: {e}")
            return None

    def release(self) -> None:
        """
        カメラリソースの解放
        必ずアプリケーション終了時に呼び出してください。
        """
        if self.camera:
            self.camera.stop()
            self.camera.close()
            self.camera = None

        if self.cap:
            self.cap.release()
            self.cap = None

    def __enter__(self):
        """コンテキストマネージャーのエントリーポイント"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャーの終了処理"""
        self.release()
        return False


class DetectionLogger:
    """
    検出結果ログ管理クラス

    YOLOの検出結果をCSVフォーマットで記録します。
    タイムスタンプ、フレームID、クラス名、信頼度、バウンディングボックス座標を保存します。

    使用例:
        logger = DetectionLogger("logs")
        logger.log_detections(frame_id=0, detections=detections)
    """

    def __init__(self, log_dir: str = "logs"):
        """
        ログ管理の初期化

        Args:
            log_dir (str): ログディレクトリ（デフォルト: 'logs'）
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # ログファイル名（タイムスタンプ付き）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"detections_{timestamp}.csv"

        # CSVヘッダーの書き込み
        with open(self.log_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'frame_id', 'class_name', 'confidence', 'x1', 'y1', 'x2', 'y2'])

        _logger.info(f"ログファイルを作成しました: {self.log_file}")

    def log_detections(self, frame_id: int,
                      detections: List[Dict[str, Any]]) -> None:
        """
        検出結果のCSVログ保存

        Args:
            frame_id (int): フレームID（0から始まる連番）
            detections (List[Dict[str, Any]]): 検出結果のリスト（YOLODetector.detect()の戻り値）
        """
        timestamp = datetime.now().isoformat()

        with open(self.log_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            for det in detections:
                bbox = det['bbox']
                writer.writerow([
                    timestamp, frame_id, det['class_name'],
                    det['confidence'], bbox[0], bbox[1], bbox[2], bbox[3]
                ])


# ============================================================================
# ユーティリティ関数
# ============================================================================
def draw_detections(image: np.ndarray, detections: List[Dict[str, Any]],
                   color: Tuple[int, int, int] = (0, 255, 0),
                   thickness: int = 2) -> np.ndarray:
    """
    画像に検出結果を描画します。
    バウンディングボックス、クラス名、信頼度スコアを画像上に描画します。

    Args:
        image (np.ndarray): 入力画像（BGRフォーマット）
        detections (List[Dict[str, Any]]): 検出結果のリスト（'bbox', 'class_name', 'confidence'を含む）
        color (Tuple[int, int, int]): バウンディングボックスの色（BGR、デフォルト: 緑）
        thickness (int): 線の太さ（デフォルト: 2）

    Returns:
        np.ndarray: バウンディングボックスとラベル描画済み画像

    使用例:
        result = draw_detections(image, detections)
        cv2.imshow("Result", result)
    """
    result_image = image.copy()

    for det in detections:
        bbox = det['bbox']
        x1, y1, x2, y2 = bbox
        confidence = det['confidence']
        class_name = det['class_name']

        # バウンディングボックスの描画
        cv2.rectangle(result_image, (x1, y1), (x2, y2), color, thickness)

        # ラベルの描画
        label = f"{class_name}: {confidence:.2f}"
        label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
        label_height = label_size[1] + 10

        # ラベル位置の決定（画面上端に近い場合はボックス内側に表示）
        if y1 - label_height < 0:
            # ボックスの内側上部にラベルを表示
            label_bg_y1 = y1
            label_bg_y2 = y1 + label_height
            label_text_y = y1 + label_size[1] + 5
        else:
            # ボックスの上にラベルを表示（通常）
            label_bg_y1 = y1 - label_height
            label_bg_y2 = y1
            label_text_y = y1 - 5

        # ラベル背景
        cv2.rectangle(result_image,
                     (x1, label_bg_y1),
                     (x1 + label_size[0], label_bg_y2),
                     color, -1)

        # ラベルテキスト
        cv2.putText(result_image, label,
                   (x1, label_text_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    return result_image


def draw_info(image: np.ndarray, fps: float, resolution: Tuple[int, int],
              inference_time: float) -> np.ndarray:
    """
    画像にパフォーマンス情報を描画します。
    FPS、解像度、推論時間を画面左上に表示します。

    Args:
        image (np.ndarray): 入力画像（BGRフォーマット）
        fps (float): 現在のフレームレート（フレーム/秒）
        resolution (Tuple[int, int]): カメラ解像度 (width, height)
        inference_time (float): 推論処理時間（ミリ秒）

    Returns:
        np.ndarray: パフォーマンス情報描画済み画像
    """
    result_image = image.copy()

    # 情報テキスト
    info_text = [
        f"FPS: {fps:.1f}",
        f"Resolution: {resolution[0]}x{resolution[1]}",
        f"Inference: {inference_time:.1f}ms"
    ]

    # 背景矩形
    text_height = 25
    bg_height = len(info_text) * text_height + 10
    cv2.rectangle(result_image, (10, 10), (300, bg_height), (0, 0, 0), -1)

    # テキスト描画
    for i, text in enumerate(info_text):
        y_pos = 30 + i * text_height
        cv2.putText(result_image, text, (15, y_pos),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    return result_image


def parse_resolution(resolution_str: str) -> Tuple[int, int]:
    """
    解像度文字列をパースします。
    "1280x720" 形式の文字列から (width, height) タプルに変換します。

    Args:
        resolution_str (str): "1280x720" 形式の文字列

    Returns:
        Tuple[int, int]: (width, height) タプル

    Raises:
        argparse.ArgumentTypeError: フォーマットが無効な場合
    """
    try:
        width, height = map(int, resolution_str.split('x'))
        return (width, height)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid resolution format: {resolution_str}")


# ============================================================================
# CLIアプリケーション
# ============================================================================
def main():
    """
    メイン関数：コマンドライン引数を処理してYOLO物体検出を実行
    Hailo-8Lを使用したリアルタイム推論とビデオ出力を管理します。
    """
    # CLIモードではログ出力を有効化
    setup_logging(level=logging.INFO,
                  format_string='%(levelname)s: %(message)s')

    parser = argparse.ArgumentParser(
        description="Raspberry Pi 5 + Hailo-8L AI Kit YOLO物体検出",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument('--model', type=str,
                       default='models/yolov8s_h8l.hef',
                       help='HEFモデルファイルのパス')

    parser.add_argument('--res', type=parse_resolution,
                       default=(1280, 720),
                       help='カメラ解像度 (例: 1280x720)')

    parser.add_argument('--conf', type=float, default=0.25,
                       help='信頼度閾値')

    parser.add_argument('--iou', type=float, default=0.45,
                       help='IoU閾値（NMS用）')

    parser.add_argument('--device', type=int, default=0,
                       help='カメラデバイスID')

    parser.add_argument('--save', action='store_true',
                       help='動画を保存する')

    parser.add_argument('--log', action='store_true',
                       help='検出結果をCSVログに保存する')

    parser.add_argument('--flip', action='store_true',
                       help='カメラ映像を上下反転する（カメラを逆さまに設置した場合）')

    parser.add_argument('--classes', type=str, nargs='+',
                       default=None,
                       help='検出対象のクラス名（スペース区切り、例: --classes person car dog）')

    parser.add_argument('--list-classes', action='store_true',
                       help='使用可能なクラス名の一覧を表示して終了')

    args = parser.parse_args()

    # クラス一覧表示モード
    if args.list_classes:
        print("使用可能なクラス名（COCO 80クラス）:")
        print("-" * 50)
        for i, name in enumerate(COCO_CLASSES):
            print(f"  {i:2d}: {name}")
        print("-" * 50)
        print(f"合計: {len(COCO_CLASSES)} クラス")
        print("\n使用例: --classes person car dog")
        return

    print("=== Raspberry Pi Hailo-8L YOLO Detector ===")
    print(f"モデル: {args.model}")
    print(f"解像度: {args.res[0]}x{args.res[1]}")
    print(f"信頼度閾値: {args.conf}")
    print(f"IoU閾値: {args.iou}")
    if args.flip:
        print("カメラ映像: 上下反転")
    if args.classes:
        print(f"検出対象クラス: {', '.join(args.classes)}")
    else:
        print("検出対象クラス: 全クラス（80種類）")

    camera = None
    video_writer = None

    try:
        # YOLODetectorの初期化
        detector = YOLODetector(
            args.model, args.conf, args.iou,
            target_classes=args.classes
        )

        # カメラマネージャーの初期化
        camera = CameraManager(args.res, args.device, flip_vertical=args.flip)

        # ログ管理の初期化
        logger = None
        if args.log:
            logger = DetectionLogger()
            print(f"ログファイル: {logger.log_file}")

        # 動画保存の準備
        if args.save:
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_dir / f"detection_{timestamp}.mp4"

            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video_writer = cv2.VideoWriter(str(output_file), fourcc, 20.0, args.res)
            print(f"動画保存: {output_file}")

        # FPS計算用変数
        fps_counter = 0
        fps_time = time.time()
        current_fps = 0.0
        frame_id = 0

        print("\n物体検出を開始します。'q'キーで終了。")

        while True:
            # フレーム読み取り
            frame = camera.read_frame()
            if frame is None:
                print("フレームを取得できませんでした")
                break

            # 推論時間の測定
            inference_start = time.time()
            detections = detector.detect(frame)
            inference_time = (time.time() - inference_start) * 1000  # ms

            # 検出結果の描画
            result_frame = draw_detections(frame, detections)

            # 情報表示の描画
            result_frame = draw_info(result_frame, current_fps, args.res, inference_time)

            # ログ保存
            if logger:
                logger.log_detections(frame_id, detections)

            # 動画保存
            if video_writer:
                video_writer.write(result_frame)

            # 画面表示
            cv2.imshow('Hailo YOLO Detection', result_frame)

            # FPS計算
            fps_counter += 1
            if fps_counter % 10 == 0:
                current_time = time.time()
                current_fps = 10 / (current_time - fps_time)
                fps_time = current_time

            frame_id += 1

            # キー入力チェック（qキーまたはESCキーで終了）
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == ord('Q') or key == 27:  # 27 = ESC
                print("\n終了キーが押されました")
                break

    except KeyboardInterrupt:
        print("\n中断されました")

    except FileNotFoundError as e:
        print(f"エラー: ファイルが見つかりません: {e}")

    except RuntimeError as e:
        print(f"エラー: {e}")

    except Exception as e:
        print(f"エラー: 予期しないエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # リソースの解放
        if camera:
            camera.release()

        if video_writer:
            video_writer.release()

        cv2.destroyAllWindows()
        print("アプリケーションを終了しました")


if __name__ == "__main__":
    main()
