#!/usr/bin/env python3
"""
サーボを指定角度に移動し、その位置で保持（トルクON）し続けるツール。

用途:
- ホーン再取り付け時の「基準位置（初期位置）」合わせ
- ネジ締め直し時に位置がズレないよう固定

注意:
- サーボを保持し続けると発熱・消費電力が増えます。作業が終わったら必ず停止してください。
- SG90は外乱（手で触る/ケーブルの押し付け等）でハンチングが収束しないことがあります。
  位置合わせだけなら --mode move-and-release / --mode move-and-pwm-off を推奨します。
"""

import argparse
import time

import servo_control


def main() -> int:
    parser = argparse.ArgumentParser(description="サーボを指定角度に固定して保持します")
    parser.add_argument(
        "--pan",
        type=float,
        default=servo_control.PAN_CENTER,
        help=f"パン角度（{servo_control.PAN_LEFT}-{servo_control.PAN_RIGHT}、デフォルト: {servo_control.PAN_CENTER}）",
    )
    parser.add_argument(
        "--tilt",
        type=float,
        default=servo_control.TILT_CENTER,
        help=f"チルト角度（{servo_control.TILT_DOWN}-{servo_control.TILT_UP}、デフォルト: {servo_control.TILT_CENTER}）",
    )
    parser.add_argument(
        "--smooth",
        action="store_true",
        help="台形制御でゆっくり移動（デフォルトは即時移動）",
    )
    parser.add_argument(
        "--mode",
        choices=["hold", "move-and-release", "move-and-pwm-off"],
        default="hold",
        help=(
            "動作モード。holdは保持（トルクON）。"
            "move-and-releaseは移動後に解放（トルクOFF）。"
            "move-and-pwm-offは移動後にPWMを強制OFF（トルクOFF）。"
        ),
    )
    parser.add_argument(
        "--refresh-seconds",
        type=float,
        default=0.0,
        help="hold中に同じ角度を再送する間隔（秒）。0で再送しない（デフォルト: 0.0）",
    )
    parser.add_argument(
        "--no-release-on-exit",
        action="store_true",
        help="停止時にサーボを解放しない（デフォルト: 解放する）",
    )
    args = parser.parse_args()

    kit = servo_control.initialize_servo_kit()

    # 位置へ移動
    servo_control.set_pan_tilt(kit, args.pan, args.tilt, smooth=args.smooth)
    print(f"MODE={args.mode} pan={args.pan:.1f} tilt={args.tilt:.1f} (Ctrl+Cで停止)")

    if args.mode == "move-and-release":
        servo_control.release_servos(kit)
        print("released servos (torque off)")
        return 0

    if args.mode == "move-and-pwm-off":
        # releaseも試しつつ、最終的にPCA9685のPWMをOFF
        try:
            servo_control.release_servos(kit)
        except Exception:
            pass
        kit._pca.channels[servo_control.PAN_CHANNEL].duty_cycle = 0
        kit._pca.channels[servo_control.TILT_CHANNEL].duty_cycle = 0
        print("PWM off (duty_cycle=0)")
        return 0

    try:
        if args.refresh_seconds <= 0:
            while True:
                time.sleep(3600)
        else:
            while True:
                # I2Cノイズや外力でズレた場合に備えて、同じ角度を定期的に再送
                servo_control.set_pan_tilt(kit, args.pan, args.tilt, smooth=False)
                time.sleep(args.refresh_seconds)
    except KeyboardInterrupt:
        print("STOP requested")
    finally:
        # デフォルトは安全のため解放する
        if not args.no_release_on_exit:
            try:
                servo_control.release_servos(kit)
                print("released servos")
            except Exception as e:
                print(f"release failed: {e}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


