"""
H5 播放页面生成模块 - 生成极简大按钮播放页面，适合老人使用
"""
import os
from datetime import datetime
import pytz
from typing import List
from news_fetcher import NewsItem
from summary_generator import get_today_blessing, truncate_summary


def generate_h5_page(
    news_items: List[NewsItem],
    audio_filename: str = "today.mp3",
    output_path: str = "docs/index.html",
):
    """
    生成 H5 播放页面

    设计原则：
    - 超大播放按钮（老人容易点）
    - 大字号
    - 高对比度
    - 简洁无干扰
    """

    shanghai_tz = pytz.timezone("Asia/Shanghai")
    now = datetime.now(shanghai_tz)
    weekday_map = ["一", "二", "三", "四", "五", "六", "日"]
    date_str = f"{now.year}年{now.month}月{now.day}日 星期{weekday_map[now.weekday()]}"

    blessing = get_today_blessing()

    # 生成新闻列表 HTML
    news_list_html = ""
    for i, item in enumerate(news_items, 1):
        summary = truncate_summary(item.summary, max_len=100)
        news_list_html += f"""
        <div class="news-item">
            <div class="news-number">{i}</div>
            <div class="news-content">
                <div class="news-title">{item.title}</div>
                {f'<div class="news-summary">{summary}</div>' if summary else ''}
                <div class="news-source">来源：{item.source}</div>
            </div>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <title>今日新闻播报</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }}

        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }}

        .header {{
            text-align: center;
            padding: 20px 0;
        }}

        .date {{
            font-size: 1.4rem;
            color: #fff;
            font-weight: 300;
            opacity: 0.95;
        }}

        .title {{
            font-size: 2rem;
            color: #fff;
            font-weight: bold;
            margin-top: 10px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }}

        .player-section {{
            background: #fff;
            border-radius: 20px;
            padding: 30px 20px;
            margin: 20px 0;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        }}

        .play-button {{
            display: inline-block;
            width: 140px;
            height: 140px;
            border-radius: 50%;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            border: none;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            box-shadow: 0 8px 25px rgba(245, 87, 108, 0.4);
            outline: none;
        }}

        .play-button:active {{
            transform: scale(0.95);
        }}

        .play-button.playing {{
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            box-shadow: 0 8px 25px rgba(79, 172, 254, 0.4);
        }}

        .play-icon {{
            font-size: 3.5rem;
            color: #fff;
            line-height: 140px;
        }}

        .play-text {{
            font-size: 1.3rem;
            color: #555;
            margin-top: 15px;
            font-weight: 500;
        }}

        .duration {{
            font-size: 1rem;
            color: #999;
            margin-top: 5px;
        }}

        audio {{
            display: none;
        }}

        .news-section {{
            background: #fff;
            border-radius: 20px;
            padding: 25px 20px;
            margin-top: 10px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.08);
        }}

        .section-title {{
            font-size: 1.5rem;
            color: #333;
            font-weight: bold;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #f5576c;
        }}

        .news-item {{
            display: flex;
            padding: 15px 0;
            border-bottom: 1px solid #f0f0f0;
        }}

        .news-item:last-child {{
            border-bottom: none;
        }}

        .news-number {{
            flex-shrink: 0;
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            font-size: 1.1rem;
            font-weight: bold;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 15px;
        }}

        .news-content {{
            flex: 1;
        }}

        .news-title {{
            font-size: 1.2rem;
            color: #222;
            line-height: 1.5;
            font-weight: 500;
        }}

        .news-summary {{
            font-size: 1rem;
            color: #666;
            line-height: 1.5;
            margin-top: 5px;
        }}

        .news-source {{
            font-size: 0.85rem;
            color: #aaa;
            margin-top: 5px;
        }}

        .blessing-section {{
            background: rgba(255,255,255,0.95);
            border-radius: 20px;
            padding: 25px 20px;
            margin-top: 20px;
            margin-bottom: 30px;
            text-align: center;
            box-shadow: 0 5px 20px rgba(0,0,0,0.08);
        }}

        .blessing-title {{
            font-size: 1.3rem;
            color: #f5576c;
            margin-bottom: 10px;
        }}

        .blessing-text {{
            font-size: 1.15rem;
            color: #555;
            line-height: 1.8;
            font-style: italic;
        }}

        .footer {{
            text-align: center;
            color: rgba(255,255,255,0.7);
            font-size: 0.85rem;
            padding: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="date">📅 {date_str}</div>
            <div class="title">📻 今日新闻</div>
        </div>

        <div class="player-section">
            <audio id="audioPlayer" preload="auto">
                <source src="audio/{audio_filename}" type="audio/mpeg">
                您的浏览器不支持音频播放。
            </audio>
            <button class="play-button" id="playBtn" onclick="togglePlay()">
                <span class="play-icon" id="playIcon">▶</span>
            </button>
            <div class="play-text" id="playText">点击收听今日新闻</div>
            <div class="duration" id="duration"></div>
        </div>

        <div class="news-section">
            <div class="section-title">📋 新闻列表（共{len(news_items)}条）</div>
            {news_list_html}
        </div>

        <div class="blessing-section">
            <div class="blessing-title">🌹 今日寄语</div>
            <div class="blessing-text">{blessing}</div>
        </div>

        <div class="footer">
            每日七点，准时为您播报天下事 ❤️
        </div>
    </div>

    <script>
        var audio = document.getElementById('audioPlayer');
        var btn = document.getElementById('playBtn');
        var icon = document.getElementById('playIcon');
        var text = document.getElementById('playText');
        var durationEl = document.getElementById('duration');
        var isPlaying = false;

        function togglePlay() {{
            if (isPlaying) {{
                audio.pause();
                icon.textContent = '▶';
                text.textContent = '继续收听';
                btn.classList.remove('playing');
                isPlaying = false;
            }} else {{
                audio.play().then(function() {{
                    icon.textContent = '⏸';
                    text.textContent = '正在播放...';
                    btn.classList.add('playing');
                    isPlaying = true;
                }}).catch(function(e) {{
                    text.textContent = '点击重试';
                }});
            }}
        }}

        audio.addEventListener('loadedmetadata', function() {{
            var mins = Math.floor(audio.duration / 60);
            var secs = Math.floor(audio.duration % 60);
            durationEl.textContent = '时长约 ' + mins + ' 分 ' + secs + ' 秒';
        }});

        audio.addEventListener('ended', function() {{
            icon.textContent = '▶';
            text.textContent = '点击重新收听';
            btn.classList.remove('playing');
            isPlaying = false;
        }});
    </script>
</body>
</html>"""

    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"📄 H5 播放页已生成: {output_path}")
