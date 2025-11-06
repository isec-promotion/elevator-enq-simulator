#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
シリアル通信デバッグテスト（PySerial + termios 版）
16バイト固定受信（VMIN=16, VTIME=5 相当）

【実行方法】
  # 利用可能なシリアルポートを検索
  python3 serial_debug_test.py test
  
  # シリアルモニタリング（ログなし）
  python3 serial_debug_test.py /dev/ttyUSB0
  
  # シリアルモニタリング（ログあり）
  python3 serial_debug_test.py /dev/ttyUSB0 --log
  python3 serial_debug_test.py /dev/ttyUSB0 --log elevator.log
  
  # ヘルプ
  python3 serial_debug_test.py help

【機能】
  - 9600bps, 8bit, Even parity, 1 stop bit設定
  - 16バイト固定受信（VMIN=16, VTIME=5）
  - オプションでログファイルに記録
  - Ctrl+Cで安全に終了
"""

import sys
import time
import signal
import termios
import serial
import os
from datetime import datetime

running = True

def handle_sigint(signum, frame):
    """Ctrl+C でループを抜ける"""
    global running
    running = False

def test_serial_ports():
    """利用可能なシリアルポートをテスト"""
    ports_to_test = [
        "/dev/ttyUSB0",
        "/dev/ttyUSB1",
        "/dev/ttyAMA0",
        "/dev/serial0",
        "/dev/ttyS0"
    ]
    print("🔍 利用可能なシリアルポートを検索中…")
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
            ser.close()
        except Exception as e:
            print(f"❌ {port}: {e}")

def monitor_serial(port="/dev/ttyUSB0", logfile=None):
    """16バイト固定受信でシリアルをモニタリング"""
    global running
    
    # ログファイルの設定
    log_file = None
    if logfile:
        if logfile is True:
            # デフォルトのログファイル名を生成
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            logfile = f"serial_debug_{timestamp}.log"
        log_path = os.path.join(os.path.dirname(__file__), logfile)
    
    try:
        # ブロッキング読み込みにするため timeout=None
        ser = serial.Serial(
            port=port,
            baudrate=9600,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_EVEN,
            stopbits=serial.STOPBITS_ONE,
            timeout=None
        )

        # termios で VMIN=16, VTIME=5 を設定
        fd = ser.fileno()
        attrs = termios.tcgetattr(fd)
        # attrs[6] は c_cc 配列
        attrs[6][termios.VMIN]  = 16   # 最低受信バイト数
        attrs[6][termios.VTIME] = 5    # 0.5秒（単位はデシ秒）
        termios.tcsetattr(fd, termios.TCSANOW, attrs)

        print(f"📡 シリアルモニタリング開始: {port}")
        print("    設定: 9600bps, 8bit, Even parity, 1 stop bit")
        print("    VMIN=16, VTIME=5 (0.5秒)")
        if logfile:
            print(f"📝 ログファイル: {log_path}")
        print("    Ctrl+C で終了\n")

        signal.signal(signal.SIGINT, handle_sigint)
        signal.signal(signal.SIGTERM, handle_sigint)

        last_activity = time.time()
        
        # ログファイルを開く
        if logfile:
            log_file = open(log_path, 'w', encoding='utf-8')
            log_file.write(f"=== シリアル通信ログ ===\n")
            log_file.write(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            log_file.write(f"ポート: {port}\n")
            log_file.write(f"設定: 9600bps, 8bit, Even parity, 1 stop bit\n")
            log_file.write(f"VMIN=16, VTIME=5 (0.5秒)\n")
            log_file.write("=" * 50 + "\n\n")
            log_file.flush()

        while running:
            # 16バイト読んで返ってくる（VMIN/VTIME に従う）
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
                if log_file:
                    log_file.write(f"[{timestamp_full}] 受信 ({len(data)} バイト)\n")
                    log_file.write(f"  HEX  : {hexstr}\n")
                    log_file.write(f"  ASCII: {ascstr}\n\n")
                    log_file.flush()
                
                last_activity = time.time()
            else:
                # タイムアウト（VTIME）で n == 0
                if time.time() - last_activity > 10:
                    wait_msg = f"[{time.strftime('%H:%M:%S')}] 待機中… (データなし)"
                    print(f"{wait_msg}\n")
                    if log_file:
                        log_file.write(f"{wait_msg}\n")
                        log_file.flush()
                    last_activity = time.time()

        print("\n🛑 モニタリング終了")
        
        # 終了時刻をログに記録
        if log_file:
            log_file.write("\n" + "=" * 50 + "\n")
            log_file.write(f"終了時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            log_file.write("=" * 50 + "\n")

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if log_file:
            log_file.close()
        if 'ser' in locals() and ser.is_open:
            ser.close()

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            test_serial_ports()
        elif sys.argv[1] == "help" or sys.argv[1] == "-h":
            print("使用方法:")
            print("  python3 serial_debug_test.py test                       # ポート検索")
            print("  python3 serial_debug_test.py /dev/ttyUSB0               # モニタリング（ログなし）")
            print("  python3 serial_debug_test.py /dev/ttyUSB0 --log         # モニタリング（自動ログ名）")
            print("  python3 serial_debug_test.py /dev/ttyUSB0 --log <file>  # モニタリング（指定ログ名）")
            print("\n例:")
            print("  python3 serial_debug_test.py /dev/ttyUSB0")
            print("  python3 serial_debug_test.py /dev/ttyUSB0 --log")
            print("  python3 serial_debug_test.py /dev/ttyUSB0 --log elevator.log")
        else:
            port = sys.argv[1]
            logfile = None
            
            # --log オプションの処理
            if len(sys.argv) > 2 and sys.argv[2] == "--log":
                if len(sys.argv) > 3:
                    # カスタムログファイル名
                    logfile = sys.argv[3]
                else:
                    # デフォルトログファイル名
                    logfile = True
            
            monitor_serial(port, logfile)
    else:
        print("使用方法:")
        print("  python3 serial_debug_test.py test                       # ポート検索")
        print("  python3 serial_debug_test.py /dev/ttyUSB0               # モニタリング（ログなし）")
        print("  python3 serial_debug_test.py /dev/ttyUSB0 --log         # モニタリング（自動ログ名）")
        print("  python3 serial_debug_test.py /dev/ttyUSB0 --log <file>  # モニタリング（指定ログ名）")
        print("\n利用可能なポートをテストします…\n")
        test_serial_ports()

if __name__ == "__main__":
    main()
