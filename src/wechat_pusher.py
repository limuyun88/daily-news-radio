"""
微信推送模块 - 通过 Server酱 推送新闻播报通知到微信
"""
import requests
from datetime import datetime
import pytz
from config import SERVERCHAN_KEY, PAGES_BASE_URL, PUSH_TITLE, PUSH_TEMPLATE


def push_to_wechat(
    news_count: int,
    audio_url: str = None,
    serverchan_key: str = None,
    url: str = None,
) -> bool:
    """
    通过 Server酱 推送消息到微信

    Args:
        news_count: 新闻条数
        audio_url: 播放页 URL（默认用配置中的 PAGES_BASE_URL）
        serverchan_key: Server酱 SendKey（默认从配置读取）
        url: 播放页 URL（优先于 audio_url）

    Returns:
        bool: 是否推送成功
    """
    key = serverchan_key or SERVERCHAN_KEY
    if not key:
        print("⚠️  未配置 SERVERCHAN_KEY，跳过微信推送")
        print("   请访问 https://sct.ftqq.com 注册获取 SendKey")
        print("   并设置环境变量: export SERVERCHAN_KEY='your_key'")
        return False

    final_url = url or audio_url or PAGES_BASE_URL
    final_url = final_url.rstrip("/")
    shanghai_tz = pytz.timezone("Asia/Shanghai")
    now = datetime.now(shanghai_tz)
    date_str = f"{now.month}月{now.day}日"

    # 构建推送内容
    desp = PUSH_TEMPLATE.format(
        date=date_str,
        count=news_count,
        url=final_url,
    )

    payload = {
        "title": PUSH_TITLE,
        "desp": desp,
    }

    try:
        # Server酱 Turbo 接口
        api_url = f"https://sctapi.ftqq.com/{key}.send"
        response = requests.post(api_url, data=payload, timeout=15)
        result = response.json()

        if result.get("code") == 0:
            print(f"✅ 微信推送成功！奶奶可以打开微信收听了")
            return True
        else:
            print(f"❌ 微信推送失败: {result}")
            return False

    except Exception as e:
        print(f"❌ 微信推送异常: {e}")
        return False


def push_simple_message(
    title: str,
    content: str,
    serverchan_key: str = None,
) -> bool:
    """
    推送简单文本消息（备用方法）

    Args:
        title: 消息标题
        content: 消息内容（支持 markdown）
        serverchan_key: Server酱 SendKey
    """
    key = serverchan_key or SERVERCHAN_KEY
    if not key:
        print("⚠️  未配置 SERVERCHAN_KEY，跳过推送")
        return False

    payload = {"title": title, "desp": content}

    try:
        api_url = f"https://sctapi.ftqq.com/{key}.send"
        response = requests.post(api_url, data=payload, timeout=15)
        result = response.json()
        return result.get("code") == 0
    except Exception as e:
        print(f"❌ 推送异常: {e}")
        return False
