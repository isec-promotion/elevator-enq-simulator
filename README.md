# エレベーター監視システム

エレベーターのシリアル通信（RS422）を監視し、リアルタイムで映像配信するシステムです。

## システム概要

このシステムは以下の 3 つのコンポーネントで構成されています：

1. **Backend（PC）**: エレベーターシミュレーター
2. **Raspberry Pi**: シリアル信号受信・映像生成・RTSP 配信
3. **動作確認ツール**: シリアル通信の動作確認

## システム構成

```
[PC（Backend）] ──RS422──> [Raspberry Pi] ──RTSP──> [クライアント]
     ↑                           ↑                      ↑
エレベーター              映像生成・配信           VLC等で視聴
シミュレーター
```

## 必要な機器

- **PC**: Windows 11（Backend 実行用）
- **Raspberry Pi**: シリアル信号受信・映像配信用
- **RS422 変換器**: USB ポートに接続
- **シリアルケーブル**: PC ↔ Raspberry Pi 間の通信用

## 通信仕様

- **通信方式**: RS422 シリアル通信
- **ボーレート**: 9600bps
- **データビット**: 8bit
- **パリティ**: Even（偶数）
- **ストップビット**: 1bit
- **プロトコル**: ENQ メッセージ（16 バイト固定）

### ENQ メッセージフォーマット

```
[ENQ][局番号4桁][コマンド][データ番号4桁][データ値4桁][チェックサム2桁]
例: 05 30 30 30 32 57 30 30 30 31 30 30 30 31 43 46
```

### データ番号定義

| データ番号 | 内容     | 値の例             |
| ---------- | -------- | ------------------ |
| 0001       | 現在階数 | 0001=1F, FFFF=B1F  |
| 0002       | 行先階   | 0003=3F, 0000=なし |
| 0003       | 荷重     | 074E=1870kg        |

## セットアップ手順

### 1. Backend（PC 側）の準備

#### 必要なソフトウェア

- Python 3.8 以上
- PySerial

#### インストール

```cmd
pip install pyserial
```

#### 設定

`backend/elevator_enq_only_simulator.py`の設定を確認：

```python
SERIAL_PORT = "COM1"  # 使用するCOMポートに変更
```

### 2. Raspberry Pi 側の準備

#### 必要なソフトウェア

- Python 3.8 以上
- GStreamer
- PySerial
- Pillow
- PyGObject

#### インストール

```bash
# システムパッケージ
sudo apt update
sudo apt install python3-pip python3-gi python3-gi-cairo gir1.2-gtk-3.0 -y
sudo apt install gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good -y
sudo apt install gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav -y
sudo apt install libgstrtspserver-1.0-dev gir1.2-gst-rtsp-server-1.0 -y

# 日本語フォント（日本語表示に必要）
sudo apt install fonts-ipafont fonts-ipafont-gothic fonts-ipafont-mincho -y

# Pythonパッケージ
pip3 install pyserial pillow
```

#### 設定

`raspberrypi/elevator_enq_rtsp_receiver.py`の設定を確認：

```python
SERIAL_PORT = "/dev/ttyUSB0"  # 使用するシリアルポートに変更
RTSP_PORT = 8554              # RTSPポート番号
```

## 使用方法

### 1. 動作確認（推奨）

まず、シリアル通信が正常に動作するか確認します。

#### Backend（PC）側でシリアルポート確認

```cmd
cd backend
python serial_debug_test.py test
```

#### Backend（PC）側でシリアル通信監視

```cmd
# ログなしでモニタリング
python serial_debug_test.py COM3

# ログありでモニタリング（自動ファイル名）
python serial_debug_test.py COM3 elevator.log

# ヘルプ表示
python serial_debug_test.py help
```

#### Raspberry Pi 側でシリアルポート確認

```bash
cd raspberrypi
python3 serial_debug_test.py test
```

#### Raspberry Pi 側でシリアル通信監視

```bash
# ログなしでモニタリング
python3 serial_debug_test.py /dev/ttyUSB0

# ログありでモニタリング（自動ファイル名）
python3 serial_debug_test.py /dev/ttyUSB0 --log

# ログありでモニタリング（カスタムファイル名）
python3 serial_debug_test.py /dev/ttyUSB0 --log elevator.log
```

### 2. システム起動

#### Backend（PC）でシミュレーター起動

```cmd
cd backend
python elevator_enq_only_simulator.py
```

オプション：

- `--port COM1`: シリアルポート指定
- `--start-floor 1`: 開始階数指定（-1:B1F, 1:1F, 2:2F, 3:3F）

#### Raspberry Pi で RTSP 配信開始

```bash
cd raspberrypi
python3 elevator_enq_rtsp_receiver.py
```

オプション：

- `--port /dev/ttyUSB0`: シリアルポート指定
- `--rtsp-port 8554`: RTSP ポート指定
- `--debug`: デバッグモード

### 3. 映像視聴

VLC メディアプレイヤーなどで以下の URL を開きます：

```
rtsp://[Raspberry PiのIPアドレス]:8554/elevator
```

例：

```
rtsp://192.168.1.100:8554/elevator
```

## 動作シーケンス

### エレベーターシミュレーター動作

1. **現在階送信**（5 回、1 秒間隔）
2. **3 秒待機**
3. **行先階送信**（5 回、1 秒間隔）
4. **3 秒待機**
5. **着床信号送信**（行先階 0000、5 回、1 秒間隔）
6. **乗客降客送信**（荷重 1870kg、5 回、1 秒間隔）
7. **5 秒待機**
8. **次のシナリオへ**

### Raspberry Pi 動作

1. **シリアル信号受信**
2. **ENQ メッセージ解析**
3. **エレベーター状態更新**
4. **映像生成**（現在階、行先階、荷重、ログ表示）
5. **RTSP 配信**

## トラブルシューティング

### シリアル通信エラー

```bash
# ポート権限確認
ls -l /dev/ttyUSB*
sudo chmod 666 /dev/ttyUSB0

# ポート使用状況確認
sudo lsof /dev/ttyUSB0
```

### RTSP 配信エラー

```bash
# GStreamerプラグイン確認
gst-inspect-1.0 | grep rtsp

# ポート使用状況確認
sudo netstat -tulpn | grep 8554
```

### 接続確認

```bash
# Raspberry Pi側でポート確認
python3 serial_debug_test.py test

# PC側でポート確認（PowerShell）
Get-WmiObject -Class Win32_SerialPort | Select-Object Name,DeviceID
```

## ログ出力例

### Backend（PC）

```
2025年06月12日 13:30:15 - INFO - 🏢 エレベーターENQ専用シミュレーター初期化
2025年06月12日 13:30:15 - INFO - ✅ シリアルポート COM1 接続成功
2025年06月12日 13:30:15 - INFO - 📤 ENQ送信: 現在階: 1F (局番号:0002 データ:0001 チェックサム:CF)
```

### Raspberry Pi

```
2025年06月12日 13:30:15 - INFO - 📤 エレベーター→ENQ: 現在階数: 1F
2025年06月12日 13:30:16 - INFO - 🚀 移動開始: 1F → 3F
2025年06月12日 13:30:20 - INFO - 🏁 着床検出: 3F (行先階クリア)
```

## ファイル構成

```
elevator-enq-simulator/
├── README.md                              # このファイル
├── .gitignore                             # Git除外設定（*.log, *.mp4）
├── backend/
│   ├── elevator_enq_only_simulator.py     # PCで動作するシミュレーター
│   └── serial_debug_test.py               # シリアル通信デバッグツール（PC用/ログ記録）
└── raspberrypi/
    ├── serial_debug_test.py               # シリアル通信デバッグツール（RPi用/--logオプション）
    └── elevator_enq_rtsp_receiver.py      # RTSP映像配信システム
```

## 技術仕様

### Backend

- **言語**: Python 3
- **主要ライブラリ**: PySerial
- **対応 OS**: Windows 11
- **通信**: RS422 シリアル送信

### Raspberry Pi

- **言語**: Python 3
- **主要ライブラリ**: GStreamer, PySerial, Pillow, PyGObject
- **対応 OS**: Raspberry Pi OS
- **機能**: シリアル受信、映像生成、RTSP 配信

### 映像仕様

- **解像度**: 640x480
- **フレームレート**: 15fps
- **エンコード**: H.264
- **配信**: RTSP

## 作成者

エレベーター監視システム開発チーム

---

## 更新履歴

- 2025/06/12: 初回リリース
  - エレベーターシミュレーター実装
  - RTSP 映像配信システム実装
  - シリアル通信動作確認ツール実装
