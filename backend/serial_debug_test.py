#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
シリアル通信デバッグテスト（Backend版）
シリアルデータを受信し、.logファイルに記録
# ポート検索
python backend/serial_debug_test.py test

# モニタリング（Windows）
python backend/serial_debug_test.py COM3

# モニタリング（Linux）
python backend/serial_debug_test.py /dev/ttyUSB0

# カスタムログファイル名を指定
python backend/serial_debug_test.py COM3 elevator.log

"""

import sys
import time
import signal
import serial
import os
from datetime import datetime

# Linuxの場合のみtermiosをインポート
try:
    import termios
    HAS_TERMIOS = True
except ImportError:
    HAS_TERMIOS = False

running = True

def handle_sigint(signum, frame):
    """Ctrl+C でループを抜ける"""
    global running
    running = False

def test_serial_ports():
    """利用可能なシリアルポートをテスト"""
    # Windows/Linux両対応
    if sys.platform.startswith('win'):
        ports_to_test = [f"COM{i}" for i in range(1, 21)]
    else:
        ports_to_test = [
            "/dev/ttyUSB0",
            "/dev/ttyUSB1",
            "/dev/ttyAMA0",
            "/dev/serial0",
            "/dev/ttyS0"
        ]
    
    print("🔍 利用可能なシリアルポートを検索中…")
    available_ports = []
    for port in ports_to_test:
        try:
            ser = serial.Serial(
                port=port,
                baudrate=9600,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_EVEN,
                stopbits=serial.STOPBITS_ONE,
                timeout=1
            )
            print(f"✅ {port}: 接続成功")
            available_ports.append(port)
            ser.close()
        except Exception as e:
            pass
    
    if not available_ports:
        print("❌ 利用可能なシリアルポートが見つかりませんでした")
    
    return available_ports

def monitor_serial(port=None, logfile=None):
    """シリアルをモニタリングし、ログファイルに記録"""
    global running
    
    # デフォルトのログファイル名を生成
    if logfile is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        logfile = f"serial_debug_{timestamp}.log"
    
    # ログファイルのパス（backend/フォルダ内）
    log_path = os.path.join(os.path.dirname(__file__), logfile)
    
    # デフォルトポートを設定
    if port is None:
        if sys.platform.startswith('win'):
            port = "COM3"
        else:
            port = "/dev/ttyUSB0"
    
    try:
        # シリアルポートを開く
        ser = serial.Serial(
            port=port,
            baudrate=9600,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_EVEN,
            stopbits=serial.STOPBITS_ONE,
            timeout=None
        )

        # Linux環境でtermiosが使える場合、VMIN/VTIME を設定
        if HAS_TERMIOS and not sys.platform.startswith('win'):
            fd = ser.fileno()
            attrs = termios.tcgetattr(fd)
            attrs[6][termios.VMIN]  = 16   # 最低受信バイト数
            attrs[6][termios.VTIME] = 5    # 0.5秒（単位はデシ秒）
            termios.tcsetattr(fd, termios.TCSANOW, attrs)
            vmin_vtime_info = "VMIN=16, VTIME=5 (0.5秒)"
        else:
            vmin_vtime_info = "ブロッキングモード"

        print(f"📡 シリアルモニタリング開始: {port}")
        print(f"    設定: 9600bps, 8bit, Even parity, 1 stop bit")
        print(f"    {vmin_vtime_info}")
        print(f"📝 ログファイル: {log_path}")
        print("    Ctrl+C で終了\n")

        signal.signal(signal.SIGINT, handle_sigint)
        signal.signal(signal.SIGTERM, handle_sigint)

        last_activity = time.time()
        
        # ログファイルを開く
        with open(log_path, 'w', encoding='utf-8') as log_file:
            # ヘッダーをログに記録
            log_file.write(f"=== シリアル通信ログ ===\n")
            log_file.write(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            log_file.write(f"ポート: {port}\n")
            log_file.write(f"設定: 9600bps, 8bit, Even parity, 1 stop bit\n")
            log_file.write("=" * 50 + "\n\n")
            log_file.flush()

            while running:
                # 16バイト読み込み
                data = ser.read(16)
                if data:
                    ts = time.strftime("%H:%M:%S")
                    timestamp_full = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                    hexstr = data.hex().upper()
                    ascstr = ''.join(
                        chr(b) if 32 <= b <= 126 else '.' for b in data
                    )
                    
                    # コンソールに表示
                    print(f"[{ts}] 受信 ({len(data)} バイト)")
                    print(f"  HEX  : {hexstr}")
                    print(f"  ASCII: {ascstr}\n")
                    
                    # ログファイルに記録
                    log_file.write(f"[{timestamp_full}] 受信 ({len(data)} バイト)\n")
                    log_file.write(f"  HEX  : {hexstr}\n")
                    log_file.write(f"  ASCII: {ascstr}\n\n")
                    log_file.flush()
                    
                    last_activity = time.time()
                else:
                    # タイムアウト
                    if time.time() - last_activity > 10:
                        wait_msg = f"[{time.strftime('%H:%M:%S')}] 待機中… (データなし)"
                        print(f"{wait_msg}\n")
                        log_file.write(f"{wait_msg}\n")
                        log_file.flush()
                        last_activity = time.time()

            # 終了時刻をログに記録
            log_file.write("\n" + "=" * 50 + "\n")
            log_file.write(f"終了時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            log_file.write("=" * 50 + "\n")

        print("\n🛑 モニタリング終了")

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            test_serial_ports()
        elif sys.argv[1] == "help" or sys.argv[1] == "-h":
            print("使用方法:")
            print("  python serial_debug_test.py test                        # ポート検索")
            print("  python serial_debug_test.py <port> [logfile]            # モニタリング")
            print("\n例:")
            if sys.platform.startswith('win'):
                print("  python serial_debug_test.py COM3")
                print("  python serial_debug_test.py COM3 elevator.log")
            else:
                print("  python serial_debug_test.py /dev/ttyUSB0")
                print("  python serial_debug_test.py /dev/ttyUSB0 elevator.log")
        else:
            port = sys.argv[1]
            logfile = sys.argv[2] if len(sys.argv) > 2 else None
            monitor_serial(port, logfile)
    else:
        print("使用方法:")
        print("  python serial_debug_test.py test                        # ポート検索")
        print("  python serial_debug_test.py <port> [logfile]            # モニタリング")
        print("\n例:")
        if sys.platform.startswith('win'):
            print("  python serial_debug_test.py COM3")
            print("  python serial_debug_test.py COM3 elevator.log")
        else:
            print("  python serial_debug_test.py /dev/ttyUSB0")
            print("  python serial_debug_test.py /dev/ttyUSB0 elevator.log")
        print("\n利用可能なポートをテストします…\n")
        test_serial_ports()

if __name__ == "__main__":
    main()
