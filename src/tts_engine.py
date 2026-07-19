"""
语音合成模块 - 使用 edge-tts 将文稿转为中文语音 mp3
"""
import edge_tts
import asyncio
import os
from typing import Optional
from config import TTS_CONFIG


async def _synthesize_segment(text: str, output_path: str, voice: str, rate: str, volume: str):
    """异步合成单段语音"""
    communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
    await communicate.save(output_path)


def synthesize_speech(
    text: str,
    output_path: str,
    voice: Optional[str] = None,
    rate: Optional[str] = None,
    volume: Optional[str] = None,
) -> bool:
    """
    将文本合成为语音 mp3 文件

    Args:
        text: 要合成的文本
        output_path: 输出 mp3 文件路径
        voice: 声音名称（默认从配置读取）
        rate: 语速（默认从配置读取）
        volume: 音量（默认从配置读取）

    Returns:
        bool: 是否成功
    """
    voice = voice or TTS_CONFIG["voice"]
    rate = rate or TTS_CONFIG["rate"]
    volume = volume or TTS_CONFIG["volume"]

    segment_length = TTS_CONFIG["segment_length"]

    try:
        # 如果文本不长，直接合成
        if len(text) <= segment_length:
            asyncio.run(_synthesize_segment(text, output_path, voice, rate, volume))
            print(f"🔊 语音合成完成: {output_path} (文本 {len(text)} 字)")
            return True

        # 长文本分段合成
        print(f"🔊 文本较长({len(text)}字)，分段合成...")
        segments = split_text(text, segment_length)
        temp_files = []

        for i, seg in enumerate(segments):
            if not seg.strip():
                continue
            temp_path = output_path.replace(".mp3", f"_part{i}.mp3")
            asyncio.run(_synthesize_segment(seg, temp_path, voice, rate, volume))
            temp_files.append(temp_path)
            print(f"  ✅ 第{i+1}段合成完成 ({len(seg)}字)")

        # 拼接音频文件
        if len(temp_files) == 1:
            os.rename(temp_files[0], output_path)
        else:
            merge_audio_files(temp_files, output_path)
            # 清理临时文件
            for f in temp_files:
                if os.path.exists(f):
                    os.remove(f)

        print(f"🔊 语音合成完成: {output_path}")
        return True

    except Exception as e:
        print(f"❌ 语音合成失败: {e}")
        return False


def split_text(text: str, max_length: int) -> list:
    """
    智能分割长文本，尽量在句号处断开
    """
    segments = []
    current = ""

    # 按段落分割
    paragraphs = text.split("\n")

    for para in paragraphs:
        if len(current) + len(para) + 1 <= max_length:
            current += para + "\n"
        else:
            if current:
                segments.append(current.strip())
                current = ""

            # 如果单段超长，按句号分割
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
    """
    合并多个 mp3 文件
    优先使用 ffmpeg，如果没有则用简单的二进制拼接
    """
    # 尝试使用 ffmpeg
    import subprocess
    try:
        # 创建文件列表
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

    # 降级方案：简单二进制拼接（mp3 可以直接拼接）
    print("  ⚠️  ffmpeg 不可用，使用二进制拼接")
    with open(output_path, "wb") as out:
        for fp in file_list:
            if os.path.exists(fp):
                with open(fp, "rb") as inp:
                    out.write(inp.read())


if __name__ == "__main__":
    # 测试
    test_text = "早上好！今天是一个美好的清晨。这是一段测试语音。"
    success = synthesize_speech(test_text, "/tmp/test_tts.mp3")
    if success:
        size = os.path.getsize("/tmp/test_tts.mp3")
        print(f"✅ 测试成功，文件大小: {size} bytes")
