# 📻 每日早间新闻语音播报

为家中的老人每天早上 7 点自动汇总国内外热门新闻 TOP10，生成语音播报，推送到微信点开即听。

## ✨ 功能特点

- **自动抓取**：从人民网、新华网、中国日报等权威 RSS 源获取新闻
- **智能筛选**：按关键词热度、来源权重、时间新鲜度选出 TOP10
- **语音播报**：edge-tts 神经网络女声合成，温暖亲切，语速适合老人
- **微信推送**：通过 Server酱 推送到奶奶的微信，点开即听
- **H5 播放页**：极简大按钮设计，老人一看就会用
- **每日祝福**：内置 32 条祝福语轮换，温暖收尾
- **全免费**：GitHub Actions + Pages + edge-tts + RSS + Server酱，零成本运行

## 📁 项目结构

```
daily-news-radio/
├── .github/workflows/
│   └── daily-news.yml          # GitHub Actions 定时任务
├── src/
│   ├── config.py               # 配置（RSS源、声音、Server酱Key等）
│   ├── news_fetcher.py         # RSS新闻抓取模块
│   ├── news_filter.py          # 新闻筛选/排序模块
│   ├── summary_generator.py    # 播报文稿生成（含祝福结尾）
│   ├── tts_engine.py           # edge-tts语音合成
│   ├── h5_page.py              # H5播放页面生成
│   ├── wechat_pusher.py        # Server酱微信推送
│   └── main.py                 # 主流程编排
├── docs/
│   ├── index.html              # H5播放页（自动生成）
│   ├── audio/today.mp3         # 今日音频（自动生成）
│   └── history/                # 历史新闻存档
├── requirements.txt
└── README.md
```

## 🚀 部署步骤

### 1. Fork 或 Clone 本仓库

```bash
git clone https://github.com/你的用户名/daily-news-radio.git
cd daily-news-radio
```

### 2. 注册 Server酱（用于微信推送）

1. 访问 [sct.ftqq.com](https://sct.ftqq.com)
2. 用**奶奶的微信**扫码登录
3. 获取 SendKey
4. 在 Server酱后台绑定微信推送通道

### 3. 配置 GitHub Secrets

在仓库 Settings → Secrets and variables → Actions 中添加：

| Secret 名称 | 值 | 说明 |
|-------------|---|------|
| `SERVERCHAN_KEY` | 你的 SendKey | Server酱推送密钥 |
| `PAGES_BASE_URL` | `https://你的用户名.github.io/daily-news-radio/` | H5页面访问地址 |
| `TIANAPI_KEY` | 你的天行API Key | 天行数据新闻API密钥（可选，增强新闻源） |
| `QWEATHER_KEY_ID` | 和风天气应用ID | 天气预报密钥（可选，增强天气数据） |
| `QWEATHER_KEY` | 和风天气应用密钥 | 天气预报密钥（可选，增强天气数据） |

### 3.1 注册天行数据（可选，推荐）

天行数据提供分类新闻API，作为RSS的补充数据源，让新闻更丰富。

1. 访问 [tianapi.com](https://www.tianapi.com/signup.html) 注册
2. 在控制台申请"综合新闻"接口
3. 获取 API Key，添加到 GitHub Secrets 的 `TIANAPI_KEY`

> 不配置也能正常运行，会自动只用 RSS 源。

### 4. 开启 GitHub Pages

在仓库 Settings → Pages：
- Source 选择 **GitHub Actions**（推荐，自动部署）
- 或选择 `main` 分支 `/docs` 目录

### 5. 测试运行

在仓库 Actions 页面：
1. 选择"每日早间新闻播报"工作流
2. 点击 "Run workflow" 手动触发测试
3. 检查运行日志和生成的文件

### 6. 确认定时任务

配置完成后，每天北京时间 **07:00** 自动运行。

> ⚠️ GitHub Actions cron 可能有 5-15 分钟延迟。如需精确 7 点，建议在 Server酱 设置延时发送，或改用自有服务器 + crontab。

## 🔧 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 安装 ffmpeg（音频拼接用）
# macOS: brew install ffmpeg
# Ubuntu: sudo apt install ffmpeg

# 设置环境变量（推送用，可选）
export SERVERCHAN_KEY="your_key"
export PAGES_BASE_URL="https://your-username.github.io/daily-news-radio/"

# 运行
cd src
python main.py
```

运行后会在 `docs/` 目录生成：
- `index.html` - H5 播放页
- `audio/today.mp3` - 语音音频
- `history/YYYY-MM-DD.txt` - 历史记录

## 🎛️ 自定义配置

编辑 `src/config.py`：

```python
# 修改语音声音（可选）
TTS_CONFIG = {
    "voice": "zh-CN-XiaoxiaoNeural",  # 晓晓（女声，温暖）默认
    # "voice": "zh-CN-YunxiNeural",   # 云希（男声，沉稳）
    # "voice": "zh-CN-YunyangNeural",  # 云扬（新闻播报风）
    "rate": "-10%",  # 语速（-10% 调慢，适合老人）
}

# 添加更多 RSS 源
RSS_FEEDS = [
    {"name": "自定义源", "url": "https://...", "category": "domestic", "weight": 1.0},
]

# 添加祝福语
BLESSINGS = [
    "你的自定义祝福语",
]
```

## 💰 成本

| 项目 | 费用 |
|------|------|
| GitHub Actions | 免费（私有仓库 2000 分钟/月，公开仓库无限） |
| GitHub Pages | 免费 |
| edge-tts | 免费，无限制 |
| RSS 源 | 免费 |
| Server酱 | 免费 5 条/天（每天只需 1 条） |
| **总计** | **0 元** |

## ❓ 常见问题

**Q: GitHub Actions 定时不准时怎么办？**
A: cron 最多可能延迟 15 分钟。如需精确，可用自有服务器 + crontab，或改用 [Vercel Cron](https://vercel.com/docs/cron-jobs)。

**Q: 奶奶不会用微信点链接怎么办？**
A: H5 页面设计为超大的播放按钮，老人只需点一下即可。Server酱推送的卡片在微信内直接点开，无需额外操作。

**Q: 音频打不开/播放不了？**
A: 确认 GitHub Pages 已开启，访问地址正确。微信内需手动点击播放按钮（微信禁止自动播放）。

**Q: 新闻质量不好/太少？**
A: 在 `config.py` 中添加更多 RSS 源，或调整筛选关键词权重。plink.anyfeeder.com 提供大量中文 RSS 源。

**Q: 想换声音怎么办？**
A: 运行 `edge-tts --list-voices | grep zh-CN` 查看所有中文声音，在 config.py 中修改。

## 📝 技术栈

- **Python 3.11** - 主语言
- **feedparser** - RSS 解析
- **edge-tts** - 微软神经网络 TTS
- **GitHub Actions** - CI/CD 定时任务
- **GitHub Pages** - 静态页面托管
- **Server酱** - 微信消息推送

## 📄 License

MIT License - 自由使用和修改

## 💝 致谢

为爱开发，让科技温暖每一位老人。
