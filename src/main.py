"""
每日早间新闻语音播报 - 主流程

完整流程：
1. 抓取 RSS 新闻
2. 筛选 TOP10
3. 生成播报文稿
4. 语音合成 mp3
5. 生成 H5 播放页
6. 推送到微信
"""
import os
import sys
import shutil
from datetime import datetime
import pytz

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import TTS_CONFIG, PAGES_BASE_URL
from news_fetcher import fetch_all_news, NewsItem
from tianapi_fetcher import fetch_tianapi_news
from news_filter import filter_top_news
from summary_generator import generate_broadcast_script, generate_text_summary
from tts_engine import synthesize_speech
from h5_page import generate_h5_page
from wechat_pusher import push_to_wechat

# 项目根目录（src 的上级）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")
AUDIO_DIR = os.path.join(DOCS_DIR, "audio")
HISTORY_DIR = os.path.join(DOCS_DIR, "history")


def save_history(news_items, script, date_str):
    """保存历史记录"""
    os.makedirs(HISTORY_DIR, exist_ok=True)
    history_file = os.path.join(HISTORY_DIR, f"{date_str}.txt")
    with open(history_file, "w", encoding="utf-8") as f:
        f.write(f"每日新闻播报 - {date_str}\n")
        f.write("=" * 50 + "\n\n")
        f.write(script)
        f.write("\n\n" + "=" * 50 + "\n")
        f.write(generate_text_summary(news_items))
    print(f"💾 历史记录已保存: {history_file}")


def main():
    """主流程"""
    shanghai_tz = pytz.timezone("Asia/Shanghai")
    now = datetime.now(shanghai_tz)
    date_str = now.strftime("%Y-%m-%d")

    print("=" * 60)
    print(f"📻 每日早间新闻语音播报")
    print(f"📅 {date_str} {now.strftime('%H:%M:%S')}")
    print("=" * 60)

    # ========== Step 1: 抓取新闻（RSS + 天行API） ==========
    print("\n📡 Step 1: 抓取新闻...")
    print("--- RSS 源 ---")
    rss_news = fetch_all_news()

    print("\n--- 天行数据API ---")
    tianapi_news = fetch_tianapi_news()

    # 合并两个数据源
    all_news = rss_news + tianapi_news
    print(f"\n📊 RSS + API 合并共 {len(all_news)} 条新闻")

    if not all_news:
        print("⚠️  未抓取到任何新闻，退出")
        return False

    # ========== Step 2: 筛选 TOP10 ==========
    print(f"\n🔍 Step 2: 筛选 TOP10...")
    top_news = filter_top_news(all_news)

    if not top_news:
        print("⚠️  筛选后无新闻，使用原始列表前10条")
        top_news = all_news[:10]

    print(f"✅ 已选出 {len(top_news)} 条新闻:")
    for i, item in enumerate(top_news, 1):
        print(f"  {i}. [{item.category}] {item.title[:40]}...")

    # ========== Step 3: 生成播报文稿 ==========
    print("\n📝 Step 3: 生成播报文稿...")
    script = generate_broadcast_script(top_news)
    print("📄 播报文稿预览（前200字）:")
    print(script[:200] + "...\n")

    # ========== Step 4: 语音合成 ==========
    print("\n🔊 Step 4: 语音合成...")
    os.makedirs(AUDIO_DIR, exist_ok=True)
    audio_path = os.path.join(AUDIO_DIR, "today.mp3")
    success = synthesize_speech(script, audio_path)

    if not success:
        print("❌ 语音合成失败，退出")
        return False

    audio_size = os.path.getsize(audio_path) / 1024  # KB
    print(f"✅ 音频文件: {audio_path} ({audio_size:.1f} KB)")

    # ========== Step 5: 生成 H5 播放页 ==========
    print("\n📄 Step 5: 生成 H5 播放页...")
    h5_path = os.path.join(DOCS_DIR, "index.html")
    generate_h5_page(top_news, "today.mp3", h5_path)

    # 保存历史记录
    save_history(top_news, script, date_str)

    # ========== Step 6: 微信推送 ==========
    print("\n📤 Step 6: 微信推送...")
    push_to_wechat(len(top_news), url=PAGES_BASE_URL.rstrip("/"))

    # ========== 完成 ==========
    print("\n" + "=" * 60)
    print("🎉 每日新闻播报生成完成！")
    print(f"   📅 日期: {date_str}")
    print(f"   📰 新闻: {len(top_news)} 条")
    print(f"   🔊 音频: {audio_path}")
    print(f"   📄 页面: {h5_path}")
    print(f"   🔗 访问: {PAGES_BASE_URL.rstrip('/')}/")
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
