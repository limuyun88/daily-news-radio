"""
语音合成模块 - 将文稿转为中文语音 mp3

双方案设计（自动降级）：
  方案A：edge-tts（微软神经网络声音，音质最佳）
  方案B：gTTS（Google Translate TTS，兼容性最好，GitHub Actions 可用）
"""
import os
import subprocess
from typing import Optional
from config import TTS_CONFIG


def synthesize_speech(
    text: str,
    output_path: str,
    voice: Optional[str] = None,
    rate: Optional[str] = None,
    volume: Optional[str] = None,
) -> bool:
    """
    将文本合成为语音 mp3 文件
    优先使用 edge-tts，失败时降级到 gTTS

    Args:
        text: 要合成的文本
        output_path: 输出 mp3 文件路径
        voice: 声音名称（edge-tts 用）
        rate: 语速
        volume: 音量

    Returns:
        bool: 是否成功
    """
    # 方案A：edge-tts
    if _try_edge_tts(text, output_path, voice, rate, volume):
        return True

    # 方案B：gTTS 降级
    print("  🔄 降级到 gTTS 语音合成...")
    if _try_gtts(text, output_path):
        return True

    print("❌ 所有语音合成方案均失败")
    return False


# ==================== 方案A：edge-tts ====================

def _try_edge_tts(text: str, output_path: str, voice, rate, volume) -> bool:
    """使用 edge-tts 合成语音"""
    try:
        import edge_tts
        import asyncio

        voice = voice or TTS_CONFIG["voice"]
        rate = rate or TTS_CONFIG["rate"]
        volume = volume or TTS_CONFIG["volume"]
        segment_length = TTS_CONFIG["segment_length"]

        async def _synthesize_segment(text, output_path, voice, rate, volume):
            communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
            await communicate.save(output_path)

        if len(text) <= segment_length:
            asyncio.run(_synthesize_segment(text, output_path, voice, rate, volume))
            print(f"✅ edge-tts 合成完成 (文本 {len(text)} 字)")
            return True

        # 长文本分段
        print(f"🔊 edge-tts 分段合成({len(text)}字)...")
        segments = split_text(text, segment_length)
        temp_files = []

        for i, seg in enumerate(segments):
            if not seg.strip():
                continue
            temp_path = output_path.replace(".mp3", f"_part{i}.mp3")
            asyncio.run(_synthesize_segment(seg, temp_path, voice, rate, volume))
            temp_files.append(temp_path)
            print(f"  ✅ 第{i+1}段完成 ({len(seg)}字)")

        if len(temp_files) == 1:
            os.rename(temp_files[0], output_path)
        else:
            merge_audio_files(temp_files, output_path)
            for f in temp_files:
                if os.path.exists(f):
                    os.remove(f)

        print(f"✅ edge-tts 合成完成")
        return True

    except Exception as e:
        print(f"⚠️  edge-tts 合成失败: {e}")
        return False


# ==================== 方案B：gTTS ====================

def _try_gtts(text: str, output_path: str) -> bool:
    """使用 gTTS 合成语音"""
    try:
        from gtts import gTTS

        # gTTS 单次限制较长文本，需要分段
        segment_length = 500  # gTTS 每段短一些更稳定
        segments = split_text(text, segment_length)

        if len(segments) <= 1:
            tts = gTTS(text, lang="zh-CN", slow=False)
            tts.save(output_path)
            print(f"✅ gTTS 合成完成 (文本 {len(text)} 字)")
            return True

        # 分段合成后拼接
        print(f"🔊 gTTS 分段合成({len(text)}字, {len(segments)}段)...")
        temp_files = []

        for i, seg in enumerate(segments):
            if not seg.strip():
                continue
            temp_path = output_path.replace(".mp3", f"_gtts_part{i}.mp3")
            tts = gTTS(seg, lang="zh-CN", slow=False)
            tts.save(temp_path)
            temp_files.append(temp_path)
            print(f"  ✅ 第{i+1}段完成 ({len(seg)}字)")

        if len(temp_files) == 1:
            os.rename(temp_files[0], output_path)
        else:
            merge_audio_files(temp_files, output_path)
            for f in temp_files:
                if os.path.exists(f):
                    os.remove(f)

        print(f"✅ gTTS 合成完成")
        return True

    except Exception as e:
        print(f"⚠️  gTTS 合成失败: {e}")
        return False


# ==================== 工具函数 ====================

def split_text(text: str, max_length: int) -> list:
    """智能分割长文本，尽量在句号处断开"""
    segments = []
    current = ""

    paragraphs = text.split("\n")

    for para in paragraphs:
        if len(current) + len(para) + 1 <= max_length:
            current += para + "\n"
        else:
            if current:
                segments.append(current.strip())
                current = ""

            if len(para) > max_length:
                sentences = para.replace("。", "。\n").split("\n")
                for sent in sentences:
                    if len(current) + len(sent) + 1 <= max_length:
                        current += sent
                    else:
                        if current:
                            segments.append(current.strip())
                        current = sent
            else:
                current = para + "\n"

    if current.strip():
        segments.append(current.strip())

    return segments


def merge_audio_files(file_list: list, output_path: str):
    """合并多个 mp3 文件，优先 ffmpeg，降级二进制拼接"""
    import subprocess
    try:
        list_file = output_path.replace(".mp3", "_list.txt")
        with open(list_file, "w") as f:
            for fp in file_list:
                f.write(f"file '{os.path.abspath(fp)}'\n")

        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", list_file, "-c", "copy", output_path],
            capture_output=True, timeout=60
        )
        os.remove(list_file)

        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return
    except Exception:
        pass

    print("  ⚠️  ffmpeg 不可用，使用二进制拼接")
    with open(output_path, "wb") as out:
        for fp in file_list:
            if os.path.exists(fp):
                with open(fp, "rb") as inp:
                    out.write(inp.read())


if __name__ == "__main__":
    test_text = "早上好！今天是一个美好的清晨。这是一段测试语音。"
    success = synthesize_speech(test_text, "/tmp/test_tts.mp3")
    if success:
        size = os.path.getsize("/tmp/test_tts.mp3")
        print(f"✅ 测试成功，文件大小: {size} bytes")
