#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
エレベーター監視システム動画生成プログラム
30秒の1080p動画を生成します
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from PIL import Image, ImageDraw, ImageFont
import cv2
import numpy as np

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 動画設定
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
VIDEO_FPS = 30
VIDEO_DURATION = 30  # 秒
TOTAL_FRAMES = VIDEO_FPS * VIDEO_DURATION

# 色設定
BACKGROUND_COLOR = (20, 30, 50)  # 濃紺背景
TEXT_COLOR_WHITE = (255, 255, 255)
TEXT_COLOR_LIGHT_GRAY = (200, 200, 200)
TEXT_COLOR_LIGHT_BLUE = (173, 216, 230)
TEXT_COLOR_YELLOW = (255, 255, 0)
TEXT_COLOR_GREEN = (144, 238, 144)
TEXT_COLOR_RED = (255, 99, 71)

# エレベーターシナリオデータ
class ElevatorScenario:
    """エレベーターシナリオ管理"""
    
    def __init__(self):
        self.scenarios = [
            {
                'name': '1階から3階への移動',
                'start_floor': '1F',
                'target_floor': '3F',
                'load_weight': 850,
                'duration': 8.0,  # 秒
                'phases': [
                    {'phase': 'waiting', 'duration': 2.0},
                    {'phase': 'moving', 'duration': 4.0},
                    {'phase': 'arrived', 'duration': 2.0}
                ]
            },
            {
                'name': '3階から地下1階への移動',
                'start_floor': '3F',
                'target_floor': 'B1F',
                'load_weight': 1200,
                'duration': 10.0,
                'phases': [
                    {'phase': 'waiting', 'duration': 2.0},
                    {'phase': 'moving', 'duration': 6.0},
                    {'phase': 'arrived', 'duration': 2.0}
                ]
            },
            {
                'name': '地下1階から2階への移動',
                'start_floor': 'B1F',
                'target_floor': '2F',
                'load_weight': 650,
                'duration': 8.0,
                'phases': [
                    {'phase': 'waiting', 'duration': 2.0},
                    {'phase': 'moving', 'duration': 4.0},
                    {'phase': 'arrived', 'duration': 2.0}
                ]
            },
            {
                'name': '待機状態',
                'start_floor': '2F',
                'target_floor': None,
                'load_weight': 0,
                'duration': 4.0,
                'phases': [
                    {'phase': 'idle', 'duration': 4.0}
                ]
            }
        ]
        
        self.communication_logs = [
            "[14:22:15] 現在階: 1F",
            "[14:22:16] 移動開始: 1F→3F",
            "[14:22:20] 着床完了: 3F",
            "[14:22:22] 荷重: 1200kg",
            "[14:22:25] 移動開始: 3F→B1F",
            "[14:22:31] 着床完了: B1F",
            "[14:22:33] 荷重: 650kg",
            "[14:22:36] 移動開始: B1F→2F",
            "[14:22:40] 着床完了: 2F",
            "[14:22:42] 荷重: 0kg"
        ]

class VideoGenerator:
    """動画生成クラス"""
    
    def __init__(self):
        self.scenario = ElevatorScenario()
        self.font_large = None
        self.font_medium = None
        self.font_small = None
        self.font_tiny = None
        self._load_fonts()
        
    def _load_fonts(self):
        """フォント読み込み"""
        font_paths = [
            "/usr/share/fonts/truetype/ipafont-mincho/ipam.ttf",  # Linux
            "/System/Library/Fonts/Hiragino Sans GB.ttc",        # macOS
            "C:/Windows/Fonts/msgothic.ttc",                     # Windows
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"    # Linux fallback
        ]
        
        font_loaded = False
        for font_path in font_paths:
            try:
                if os.path.exists(font_path):
                    self.font_large = ImageFont.truetype(font_path, 96)
                    self.font_medium = ImageFont.truetype(font_path, 64)
                    self.font_small = ImageFont.truetype(font_path, 40)
                    self.font_tiny = ImageFont.truetype(font_path, 32)
                    logger.info(f"✅ フォント読み込み成功: {font_path}")
                    font_loaded = True
                    break
            except (IOError, OSError) as e:
                logger.debug(f"フォント読み込み失敗: {font_path} - {e}")
                continue
        
        if not font_loaded:
            logger.warning("⚠️ システムフォントが見つかりません。デフォルトフォントを使用します")
            self.font_large = ImageFont.load_default()
            self.font_medium = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
            self.font_tiny = ImageFont.load_default()

    def _draw_centered_text(self, draw: ImageDraw.Draw, text: str, font: ImageFont.ImageFont, 
                           x: int, y: int, color: Tuple[int, int, int]):
        """中央揃えテキスト描画"""
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            draw.text((x - text_width//2, y - text_height//2), text, font=font, fill=color)
        except Exception as e:
            # フォールバック: 簡易的な中央揃え
            draw.text((x - len(text) * 10, y - 10), text, font=font, fill=color)

    def _get_scenario_state(self, frame_num: int) -> dict:
        """フレーム番号から現在のシナリオ状態を取得"""
        current_time = frame_num / VIDEO_FPS
        elapsed_time = 0.0
        
        for scenario in self.scenario.scenarios:
            if elapsed_time + scenario['duration'] > current_time:
                # このシナリオ内の時間
                scenario_time = current_time - elapsed_time
                
                # フェーズ判定
                phase_elapsed = 0.0
                current_phase = 'waiting'
                
                for phase in scenario['phases']:
                    if phase_elapsed + phase['duration'] > scenario_time:
                        current_phase = phase['phase']
                        break
                    phase_elapsed += phase['duration']
                
                return {
                    'scenario': scenario,
                    'phase': current_phase,
                    'scenario_time': scenario_time,
                    'total_time': current_time
                }
            
            elapsed_time += scenario['duration']
        
        # 最後のシナリオを返す
        return {
            'scenario': self.scenario.scenarios[-1],
            'phase': 'idle',
            'scenario_time': 0.0,
            'total_time': current_time
        }

    def _get_communication_logs(self, current_time: float) -> List[str]:
        """現在時刻に応じた通信ログを取得"""
        # 時間に応じてログを段階的に表示
        log_count = min(len(self.scenario.communication_logs), 
                       int(current_time / 3) + 1)  # 3秒ごとに1つずつ追加
        return self.scenario.communication_logs[:log_count]

    def generate_frame(self, frame_num: int) -> Image.Image:
        """フレーム生成"""
        # 背景画像作成
        img = Image.new('RGB', (VIDEO_WIDTH, VIDEO_HEIGHT), BACKGROUND_COLOR)
        draw = ImageDraw.Draw(img)
        
        # 現在の状態取得
        state = self._get_scenario_state(frame_num)
        scenario = state['scenario']
        phase = state['phase']
        current_time = state['total_time']
        
        # 現在時刻（動画開始から経過時間を基準とした仮想時刻）
        base_time = datetime(2025, 8, 25, 14, 22, 0)
        virtual_time = base_time + timedelta(seconds=current_time)
        timestamp = virtual_time.strftime("%Y年%m月%d日 %H:%M:%S")
        
        # タイトル
        title = "エレベーター監視システム（デモ動画）"
        self._draw_centered_text(draw, title, self.font_medium, VIDEO_WIDTH//2, 80, TEXT_COLOR_WHITE)
        
        # 現在時刻表示
        self._draw_centered_text(draw, timestamp, self.font_small, VIDEO_WIDTH//2, 140, TEXT_COLOR_LIGHT_GRAY)
        
        # 接続状態表示
        self._draw_centered_text(draw, "接続状態: 接続中", self.font_small, VIDEO_WIDTH//2, 180, TEXT_COLOR_GREEN)
        
        # 解像度情報表示
        resolution_info = f"解像度: {VIDEO_WIDTH}x{VIDEO_HEIGHT}@{VIDEO_FPS}fps (1080p)"
        self._draw_centered_text(draw, resolution_info, self.font_tiny, VIDEO_WIDTH//2, 210, (128, 128, 128))
        
        # エレベーター状態表示
        y_pos = 300
        
        # 状態に応じた表示
        if phase == 'moving':
            status_text = f"{scenario['start_floor']} ⇒ {scenario['target_floor']}"
            status_color = TEXT_COLOR_YELLOW
            status_bg = (100, 100, 0)
            status_border = (255, 165, 0)  # オレンジ
        elif phase == 'arrived':
            status_text = f"現在階: {scenario['target_floor']}"
            status_color = TEXT_COLOR_GREEN
            status_bg = (0, 100, 0)
            status_border = TEXT_COLOR_GREEN
        elif phase == 'idle':
            status_text = f"現在階: {scenario['start_floor']} (待機中)"
            status_color = TEXT_COLOR_LIGHT_BLUE
            status_bg = (0, 50, 100)
            status_border = TEXT_COLOR_LIGHT_BLUE
        else:  # waiting
            status_text = f"現在階: {scenario['start_floor']}"
            status_color = TEXT_COLOR_GREEN
            status_bg = (0, 100, 0)
            status_border = TEXT_COLOR_GREEN
        
        # 状態背景
        status_rect = [40, y_pos-60, VIDEO_WIDTH-40, y_pos+60]
        draw.rectangle(status_rect, fill=status_bg, outline=status_border, width=3)
        
        # 状態テキスト
        self._draw_centered_text(draw, status_text, self.font_large, VIDEO_WIDTH//2, y_pos, status_color)
        
        # 詳細情報
        y_pos = 450
        details = [
            f"荷重: {scenario['load_weight']}kg",
            f"シナリオ: {scenario['name']}",
            f"フェーズ: {phase}",
            f"経過時間: {current_time:.1f}秒"
        ]
        
        for detail in details:
            self._draw_centered_text(draw, detail, self.font_small, VIDEO_WIDTH//2, y_pos, TEXT_COLOR_LIGHT_BLUE)
            y_pos += 50
        
        # 通信ログ表示
        y_pos = 650
        draw.text((40, y_pos), "ENQ受信ログ:", font=self.font_small, fill=TEXT_COLOR_WHITE)
        y_pos += 45
        
        # 現在時刻に応じたログを表示
        logs = self._get_communication_logs(current_time)
        for log_entry in logs[-8:]:  # 最新8件を表示
            draw.text((40, y_pos), log_entry, font=self.font_tiny, fill=TEXT_COLOR_LIGHT_GRAY)
            y_pos += 36
        
        # プログレスバー表示
        progress = frame_num / TOTAL_FRAMES
        progress_width = VIDEO_WIDTH - 80
        progress_height = 20
        progress_x = 40
        progress_y = VIDEO_HEIGHT - 60
        
        # プログレスバー背景
        draw.rectangle([progress_x, progress_y, progress_x + progress_width, progress_y + progress_height], 
                      fill=(50, 50, 50), outline=TEXT_COLOR_LIGHT_GRAY, width=2)
        
        # プログレスバー進行
        progress_fill_width = int(progress_width * progress)
        if progress_fill_width > 0:
            draw.rectangle([progress_x, progress_y, progress_x + progress_fill_width, progress_y + progress_height], 
                          fill=(0, 150, 255))
        
        # プログレス表示
        progress_text = f"動画進行: {progress*100:.1f}% ({frame_num}/{TOTAL_FRAMES}フレーム)"
        self._draw_centered_text(draw, progress_text, self.font_tiny, VIDEO_WIDTH//2, progress_y - 25, TEXT_COLOR_LIGHT_GRAY)
        
        return img

    def generate_video(self, output_path: str):
        """動画生成"""
        logger.info(f"🎬 動画生成開始: {output_path}")
        logger.info(f"📐 解像度: {VIDEO_WIDTH}x{VIDEO_HEIGHT}")
        logger.info(f"🎞️ フレームレート: {VIDEO_FPS}fps")
        logger.info(f"⏱️ 動画時間: {VIDEO_DURATION}秒")
        logger.info(f"🖼️ 総フレーム数: {TOTAL_FRAMES}")
        
        # OpenCV VideoWriter設定
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, VIDEO_FPS, (VIDEO_WIDTH, VIDEO_HEIGHT))
        
        if not out.isOpened():
            logger.error("❌ 動画ファイルの作成に失敗しました")
            return False
        
        try:
            start_time = time.time()
            
            for frame_num in range(TOTAL_FRAMES):
                # フレーム生成
                pil_image = self.generate_frame(frame_num)
                
                # PIL Image → OpenCV形式変換
                cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
                
                # フレーム書き込み
                out.write(cv_image)
                
                # 進行状況表示
                if frame_num % (VIDEO_FPS * 2) == 0:  # 2秒ごと
                    progress = (frame_num + 1) / TOTAL_FRAMES * 100
                    elapsed = time.time() - start_time
                    eta = elapsed / (frame_num + 1) * (TOTAL_FRAMES - frame_num - 1)
                    logger.info(f"📊 進行状況: {progress:.1f}% ({frame_num+1}/{TOTAL_FRAMES}) "
                              f"経過: {elapsed:.1f}s 残り: {eta:.1f}s")
            
            out.release()
            
            total_time = time.time() - start_time
            logger.info(f"✅ 動画生成完了!")
            logger.info(f"⏱️ 生成時間: {total_time:.1f}秒")
            logger.info(f"📁 出力ファイル: {output_path}")
            
            # ファイルサイズ確認
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
                logger.info(f"📦 ファイルサイズ: {file_size:.1f}MB")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 動画生成エラー: {e}")
            out.release()
            return False

def main():
    """メイン処理"""
    logger.info("🎬 エレベーター監視システム動画生成プログラム")
    
    # 出力ファイル名生成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"elevator_demo_{timestamp}.mp4"
    output_path = os.path.join(os.path.dirname(__file__), output_filename)
    
    # 動画生成
    generator = VideoGenerator()
    
    try:
        success = generator.generate_video(output_path)
        
        if success:
            logger.info("🎉 動画生成が正常に完了しました!")
            logger.info(f"📺 生成された動画: {output_path}")
            logger.info("💡 VLCメディアプレイヤーなどで再生できます")
        else:
            logger.error("❌ 動画生成に失敗しました")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("\n🛑 ユーザーによって中断されました")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ 予期しないエラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
