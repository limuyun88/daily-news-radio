"""
天气信息抓取模块 - 为播报提供当天天气数据

三方案设计（自动降级）：
  方案A（优先）：和风天气 API，数据最全（温度/风力/湿度/AQI/穿衣建议）
  方案B（次选）：wttr.in，免注册，英文需转中文
  方案C（兜底）：中央气象台，免注册

注册和风天气：https://dev.qweather.com/
"""
import os
import time
import hmac
import base64
import hashlib
import json
import requests
from dataclasses import dataclass
from typing import Optional

from config import WEATHER_CONFIG


@dataclass
class WeatherInfo:
    """天气数据结构"""
    city: str = ""
    temperature: str = ""          # 当前温度
    feels_like: str = ""           # 体感温度
    description: str = ""          # 天气描述（晴/多云等）
    wind_dir: str = ""             # 风向
    wind_scale: str = ""           # 风力等级
    humidity: str = ""             # 湿度
    aqi: str = ""                  # 空气质量指数
    aqi_category: str = ""         # 空气质量等级（优/良等）
    dressing_advice: str = ""      # 穿衣建议
    today_temp_max: str = ""       # 今日最高温
    today_temp_min: str = ""       # 今日最低温
    uv_advice: str = ""            # 紫外线建议
    source: str = ""               # 数据来源


# 英文天气描述 → 中文映射
WEATHER_DESC_MAP = {
    "clear": "晴", "sunny": "晴",
    "partly cloudy": "多云", "partly cloudy ": "多云",
    "cloudy": "阴", "overcast": "阴天",
    "mist": "薄雾", "fog": "雾", "foggy": "雾",
    "patchy rain nearby": "小雨", "patchy rain": "小雨",
    "light rain": "小雨", "light drizzle": "毛毛雨",
    "moderate rain": "中雨", "heavy rain": "大雨",
    "light snow": "小雪", "moderate snow": "中雪", "heavy snow": "大雪",
    "thundery outbreaks": "雷阵雨", "thunder": "雷阵雨",
    "patchy light rain": "零星小雨",
    "patchy snow nearby": "零星小雪",
}

# 风向英文 → 中文
WIND_DIR_MAP = {
    "N": "北风", "NNE": "北东北风", "NE": "东北风", "ENE": "东东北风",
    "E": "东风", "ESE": "东东南风", "SE": "东南风", "SSE": "南东南风",
    "S": "南风", "SSW": "南西南风", "SW": "西南风", "WSW": "西西南风",
    "W": "西风", "WNW": "西西北风", "NW": "西北风", "NNW": "北西北风",
}


def _translate_weather_desc(desc: str) -> str:
    """英文天气描述转中文"""
    if not desc:
        return ""
    desc_lower = desc.strip().lower()
    # 精确匹配
    if desc_lower in WEATHER_DESC_MAP:
        return WEATHER_DESC_MAP[desc_lower]
    # 模糊匹配
    for key, val in WEATHER_DESC_MAP.items():
        if key in desc_lower:
            return val
    return desc  # 找不到就返回原文


def _translate_wind_dir(direction: str) -> str:
    """风向英文转中文"""
    return WIND_DIR_MAP.get(direction.strip().upper(), direction)


# ==================== 方案A：和风天气 ====================

def _make_jwt(key_id: str, key: str) -> str:
    """生成和风天气 JWT 鉴权 token"""
    def b64encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    header = {"alg": "HS256", "typ": "JWT"}
    now_ts = int(time.time())
    payload = {"sub": key_id, "iat": now_ts - 30, "exp": now_ts + 900}

    header_b64 = b64encode(json.dumps(header).encode())
    payload_b64 = b64encode(json.dumps(payload).encode())
    message = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(key.encode(), message, hashlib.sha256).digest()
    sig_b64 = b64encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def _fetch_qweather(weather_info: WeatherInfo, key_id: str, key: str, location: str) -> bool:
    """通过和风天气API获取天气"""
    try:
        jwt = _make_jwt(key_id, key)

        # 1. 查找城市 LocationID
        geo_url = "https://geoapi.qweather.com/v2/city/lookup"
        geo_resp = requests.get(
            geo_url,
            params={"location": location, "jwt": jwt},
            timeout=10
        ).json()

        if geo_resp.get("code") != "200" or not geo_resp.get("location"):
            print(f"  ⚠️  和风天气：未找到城市 '{location}'")
            return False

        loc_id = geo_resp["location"][0]["id"]
        weather_info.city = geo_resp["location"][0].get("name", location)

        jwt = _make_jwt(key_id, key)

        # 2. 实时天气
        now_url = "https://devapi.qweather.com/v7/weather/now"
        now_resp = requests.get(
            now_url,
            params={"location": loc_id, "jwt": jwt},
            timeout=10
        ).json()

        if now_resp.get("code") == "200":
            now = now_resp["now"]
            weather_info.temperature = now.get("temp", "")
            weather_info.feels_like = now.get("feelsLike", "")
            weather_info.description = now.get("text", "")
            weather_info.wind_dir = now.get("windDir", "")
            weather_info.wind_scale = now.get("windScale", "")
            weather_info.humidity = now.get("humidity", "")

        jwt = _make_jwt(key_id, key)

        # 3. 今日天气预报（最高/最低温）
        daily_url = "https://devapi.qweather.com/v7/weather/3d"
        daily_resp = requests.get(
            daily_url,
            params={"location": loc_id, "jwt": jwt},
            timeout=10
        ).json()

        if daily_resp.get("code") == "200" and daily_resp.get("daily"):
            today = daily_resp["daily"][0]
            weather_info.today_temp_max = today.get("tempMax", "")
            weather_info.today_temp_min = today.get("tempMin", "")

        jwt = _make_jwt(key_id, key)

        # 4. 空气质量 AQI
        aqi_url = "https://devapi.qweather.com/v7/air/now"
        aqi_resp = requests.get(
            aqi_url,
            params={"location": loc_id, "jwt": jwt},
            timeout=10
        ).json()

        if aqi_resp.get("code") == "200" and aqi_resp.get("now"):
            aqi = aqi_resp["now"]
            weather_info.aqi = aqi.get("aqi", "")
            weather_info.aqi_category = aqi.get("category", "")

        jwt = _make_jwt(key_id, key)

        # 5. 生活指数（穿衣=3，紫外线=5）
        indices_url = "https://devapi.qweather.com/v7/indices/1d"
        indices_resp = requests.get(
            indices_url,
            params={"location": loc_id, "type": "3,5", "jwt": jwt},
            timeout=10
        ).json()

        if indices_resp.get("code") == "200" and indices_resp.get("daily"):
            for idx in indices_resp["daily"]:
                if idx.get("type") == "3":
                    weather_info.dressing_advice = idx.get("text", "")
                elif idx.get("type") == "5":
                    weather_info.uv_advice = idx.get("text", "")

        weather_info.source = "和风天气"
        print(f"  ✅ 和风天气：{weather_info.city} {weather_info.temperature}°C {weather_info.description}")
        return True

    except Exception as e:
        print(f"  ⚠️  和风天气获取失败: {e}")
        return False


# ==================== 方案B：wttr.in（免注册） ====================

def _fetch_wttr(weather_info: WeatherInfo, city: str) -> bool:
    """通过 wttr.in 获取天气（无需注册）"""
    try:
        # 使用英文城市名查询更稳定
        city_en_map = {
            "武汉": "Wuhan", "北京": "Beijing", "上海": "Shanghai",
            "广州": "Guangzhou", "深圳": "Shenzhen", "成都": "Chengdu",
            "杭州": "Hangzhou", "南京": "Nanjing", "西安": "Xian",
            "重庆": "Chongqing", "长沙": "Changsha", "天津": "Tianjin",
        }
        query_city = city_en_map.get(city, city)

        url = f"https://wttr.in/{query_city}?format=j1"
        resp = requests.get(url, timeout=15, headers={"Accept-Language": "zh-CN"})
        data = resp.json()

        current = data.get("current_condition", [{}])[0]
        weather_info.city = city
        weather_info.temperature = current.get("temp_C", "")
        weather_info.feels_like = current.get("FeelsLikeC", "")
        weather_info.humidity = current.get("humidity", "")

        # 天气描述（英文转中文）
        desc_en = current.get("lang_zh", [{}])[0].get("value", "") or \
                  current.get("weatherDesc", [{}])[0].get("value", "")
        weather_info.description = _translate_weather_desc(desc_en)

        # 风向风力
        wind_dir_en = current.get("winddir16Point", "")
        weather_info.wind_dir = _translate_wind_dir(wind_dir_en)
        wind_kmph = current.get("windspeedKmph", "0")
        try:
            # km/h 转蒲福风级
            kmph = int(wind_kmph)
            if kmph < 2:
                weather_info.wind_scale = "0"
            elif kmph < 6:
                weather_info.wind_scale = "1"
            elif kmph < 12:
                weather_info.wind_scale = "2"
            elif kmph < 20:
                weather_info.wind_scale = "3"
            elif kmph < 29:
                weather_info.wind_scale = "4"
            elif kmph < 39:
                weather_info.wind_scale = "5"
            elif kmph < 50:
                weather_info.wind_scale = "6"
            else:
                weather_info.wind_scale = "7"
        except (ValueError, TypeError):
            weather_info.wind_scale = "1"

        # 今日最高/最低温
        today = data.get("weather", [{}])[0]
        if today:
            weather_info.today_temp_max = today.get("maxtempC", "")
            weather_info.today_temp_min = today.get("mintempC", "")

        weather_info.source = "wttr.in"
        print(f"  ✅ wttr.in：{weather_info.city} {weather_info.temperature}°C {weather_info.description}")
        return True

    except Exception as e:
        print(f"  ⚠️  wttr.in获取失败: {e}")
        return False


# ==================== 方案C：中央气象台（兜底） ====================

CMA_STATION_IDS = {
    "武汉": "57494", "北京": "54511", "上海": "58367",
    "广州": "59287", "深圳": "59493", "成都": "56294",
    "杭州": "58457", "南京": "58238", "西安": "57036", "重庆": "57516",
}

def _fetch_cma(weather_info: WeatherInfo, city: str) -> bool:
    """通过中央气象台API获取天气"""
    try:
        station_id = CMA_STATION_IDS.get(city, "57494")

        url = f"https://weather.cma.cn/api/weather/{station_id}"
        resp = requests.get(url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/json",
        })
        data = resp.json()

        if data.get("status") != "ok":
            print(f"  ⚠️  中央气象台返回异常")
            return False

        now = data.get("data", {}).get("now", {})
        weather_info.city = city
        weather_info.temperature = now.get("temperature", "")
        weather_info.description = now.get("weather", "")
        weather_info.wind_dir = now.get("windDirection", "")
        weather_info.wind_scale = now.get("windScale", "")
        weather_info.humidity = now.get("humidity", "")

        daily = data.get("data", {}).get("daily", [])
        if daily and len(daily) > 0:
            weather_info.today_temp_max = daily[0].get("day", {}).get("tempMax", "")
            weather_info.today_temp_min = daily[0].get("night", {}).get("tempMin", "")

        weather_info.source = "中央气象台"
        print(f"  ✅ 中央气象台：{weather_info.city} {weather_info.temperature}°C {weather_info.description}")
        return True

    except Exception as e:
        print(f"  ⚠️  中央气象台获取失败: {e}")
        return False


# ==================== 主入口 ====================

def fetch_weather() -> WeatherInfo:
    """
    获取天气信息

    优先级：和风天气 → wttr.in → 中央气象台
    """
    info = WeatherInfo()
    city = WEATHER_CONFIG.get("city", "武汉")

    print(f"🌤️  获取天气信息（{city}）...")

    # 方案A：和风天气（需要Key，数据最全）
    qweather_key_id = os.environ.get("QWEATHER_KEY_ID", "")
    qweather_key = os.environ.get("QWEATHER_KEY", "")

    if qweather_key_id and qweather_key:
        if _fetch_qweather(info, qweather_key_id, qweather_key, city):
            return info

    # 方案B：wttr.in（免注册，数据较全）
    if _fetch_wttr(info, city):
        return info

    # 方案C：中央气象台（兜底）
    if _fetch_cma(info, city):
        return info

    # 全部失败
    print("  ⚠️  天气获取失败，将跳过天气播报")
    return info


def format_weather_for_speech(weather: WeatherInfo) -> str:
    """
    将天气信息转为口语化播报文案

    格式：先报城市和天气概况，再报温度体感，再报风力湿度，再报AQI和穿衣建议
    """
    if not weather.city and not weather.temperature:
        return ""

    parts = []

    # 城市和天气概况
    if weather.city and weather.description:
        parts.append(f"今天{weather.city}天气{weather.description}")

    # 温度和体感
    if weather.temperature:
        temp_str = f"当前气温{weather.temperature}度"
        if weather.feels_like:
            temp_str += f"，体感温度{weather.feels_like}度"
        if weather.today_temp_max and weather.today_temp_min:
            temp_str += f"，今日{weather.today_temp_min}到{weather.today_temp_max}度"
        parts.append(temp_str)

    # 风力和湿度
    wind_humidity = []
    if weather.wind_dir and weather.wind_scale:
        wind_humidity.append(f"{weather.wind_dir}{weather.wind_scale}级")
    elif weather.wind_dir:
        wind_humidity.append(weather.wind_dir)
    if weather.humidity:
        wind_humidity.append(f"湿度{weather.humidity}%")
    if wind_humidity:
        parts.append("，".join(wind_humidity))

    # 空气质量
    if weather.aqi and weather.aqi_category:
        parts.append(f"空气质量指数{weather.aqi}，{weather.aqi_category}")

    # 穿衣建议
    if weather.dressing_advice:
        advice = weather.dressing_advice
        if len(advice) > 60:
            period_pos = advice.find("。")
            if 0 < period_pos < 60:
                advice = advice[:period_pos + 1]
            else:
                advice = advice[:60] + "。"
        parts.append(f"穿衣建议：{advice}")

    if not parts:
        return ""

    # 组合成口语化播报
    speech = "。".join(parts) + "。"
    return f"首先为您播报今日天气。{speech}"


if __name__ == "__main__":
    # 测试
    weather = fetch_weather()
    print()
    print("天气播报文案：")
    print(format_weather_for_speech(weather))
