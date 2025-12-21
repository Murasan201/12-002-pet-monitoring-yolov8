#!/usr/bin/env python3
"""
パン・チルト可動域の単体テスト（追跡/検出なし）

目的:
- サーボHAT(PCA9685) + SG90 + 電源の状態で、指定角度に問題なく到達できるか確認する
- 追従ロジックや検出ロジックの影響を排除して切り分ける

注意:
- 動作中に機構へ指を入れないこと（挟み込み注意）
- 異音/引っ掛かり/過大な振動が出たらすぐ Ctrl+C
"""

import argparse
import time
from datetime import datetime
from pathlib import Path

import servo_control


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="パン・チルト可動域テスト（単体）")

    p.add_argument("--pan-left", type=float, default=servo_control.PAN_LEFT)
    p.add_argument("--pan-right", type=float, default=servo_control.PAN_RIGHT)
    p.add_argument("--tilt-down", type=float, default=servo_control.TILT_DOWN)
    p.add_argument("--tilt-up", type=float, default=servo_control.TILT_UP)
    p.add_argument("--pan-center", type=float, default=servo_control.PAN_CENTER)
    p.add_argument("--tilt-center", type=float, default=servo_control.TILT_CENTER)

    p.add_argument("--smooth", action="store_true", help="台形制御でゆっくり移動（デフォルト: 即時）")
    p.add_argument("--sleep", type=float, default=1.0, help="各位置で停止する秒数（デフォルト: 1.0）")
    p.add_argument(
        "--pattern",
        choices=["corners", "sweep-pan", "sweep-tilt", "all"],
        default="corners",
        help="corners: 端点中心の確認 / sweep: 軸方向スイープ / all: 全部",
    )
    p.add_argument(
        "--step",
        type=float,
        default=5.0,
        help="sweep時のステップ角（デフォルト: 5.0度）",
    )

    p.add_argument(
        "--log",
        type=str,
        default="",
        help="CSVログ出力先（例: logs/pan_tilt_range.csv）。未指定ならログなし",
    )

    return p.parse_args()


def frange(start: float, stop: float, step: float):
    # stopを含める簡易フロートレンジ
    if step <= 0:
        raise ValueError("step must be > 0")
    x = start
    if start <= stop:
        while x <= stop + 1e-9:
            yield x
            x += step
    else:
        while x >= stop - 1e-9:
            yield x
            x -= step


def move_and_wait(kit, pan: float, tilt: float, smooth: bool, sleep_s: float, label: str):
    print(f"{label}: pan={pan:.1f} tilt={tilt:.1f}")
    servo_control.set_pan_tilt(kit, pan, tilt, smooth=smooth)
    time.sleep(max(0.0, sleep_s))


def main() -> int:
    args = parse_args()

    kit = servo_control.initialize_servo_kit()
    log_f = None
    if args.log:
        log_path = Path(args.log)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_f = open(str(log_path), "w", encoding="utf-8", newline="")
        log_f.write("ts_iso,label,pan_cmd,tilt_cmd,pan_read,tilt_read\n")

    try:
        print("=== Pan/Tilt Range Test ===")
        print(f"PAN : left={args.pan_left} center={args.pan_center} right={args.pan_right}")
        print(f"TILT: down={args.tilt_down} center={args.tilt_center} up={args.tilt_up}")
        print(f"smooth={args.smooth} sleep={args.sleep}s pattern={args.pattern}")
        if args.log:
            print(f"log: {args.log}")
        print("Ctrl+Cで中断できます。")
        print()

        # まず中央へ
        def log_row(label: str, pan_cmd: float, tilt_cmd: float):
            if not log_f:
                return
            # ServoKitのangleは「最後に指令した角度」が返ることが多い（実角度センサは無い）
            try:
                pan_read = kit.servo[servo_control.PAN_CHANNEL].angle
            except Exception:
                pan_read = None
            try:
                tilt_read = kit.servo[servo_control.TILT_CHANNEL].angle
            except Exception:
                tilt_read = None

            ts_iso = datetime.now().isoformat(timespec="milliseconds")
            log_f.write(
                f"{ts_iso},{label},{pan_cmd:.2f},{tilt_cmd:.2f},{'' if pan_read is None else f'{pan_read:.2f}'},{'' if tilt_read is None else f'{tilt_read:.2f}'}\n"
            )

        def move_wait_log(label: str, pan: float, tilt: float):
            move_and_wait(kit, pan, tilt, smooth=args.smooth, sleep_s=args.sleep, label=label)
            log_row(label, pan, tilt)

        move_wait_log("CENTER", args.pan_center, args.tilt_center)

        def corners():
            move_wait_log("LEFT-DOWN", args.pan_left, args.tilt_down)
            move_wait_log("RIGHT-DOWN", args.pan_right, args.tilt_down)
            move_wait_log("RIGHT-UP", args.pan_right, args.tilt_up)
            move_wait_log("LEFT-UP", args.pan_left, args.tilt_up)
            move_wait_log("CENTER", args.pan_center, args.tilt_center)

        def sweep_pan():
            print("SWEEP PAN (tilt=center)")
            for pan in frange(args.pan_left, args.pan_right, args.step):
                move_wait_log("PAN", pan, args.tilt_center)
            for pan in frange(args.pan_right, args.pan_left, args.step):
                move_wait_log("PAN", pan, args.tilt_center)
            move_wait_log("CENTER", args.pan_center, args.tilt_center)

        def sweep_tilt():
            print("SWEEP TILT (pan=center)")
            for tilt in frange(args.tilt_down, args.tilt_up, args.step):
                move_wait_log("TILT", args.pan_center, tilt)
            for tilt in frange(args.tilt_up, args.tilt_down, args.step):
                move_wait_log("TILT", args.pan_center, tilt)
            move_wait_log("CENTER", args.pan_center, args.tilt_center)

        if args.pattern in ("corners", "all"):
            corners()
        if args.pattern in ("sweep-pan", "all"):
            sweep_pan()
        if args.pattern in ("sweep-tilt", "all"):
            sweep_tilt()

        print("OK: test finished")
        return 0

    except KeyboardInterrupt:
        print("\nInterrupted")
        return 130

    finally:
        if log_f:
            try:
                log_f.flush()
                log_f.close()
            except Exception:
                pass
        # 安全のため中央へ戻して解放
        try:
            servo_control.set_center_position(kit, smooth=True)
            time.sleep(0.5)
        except Exception:
            pass
        try:
            servo_control.release_servos(kit)
        except Exception:
            # 最終手段: PWM off
            try:
                kit._pca.channels[servo_control.PAN_CHANNEL].duty_cycle = 0
                kit._pca.channels[servo_control.TILT_CHANNEL].duty_cycle = 0
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())


