import os
from app.reels_maker import ReelsMaker, ReelsMakerConfig
import pytest


@pytest.mark.asyncio
async def test_reels_maker():
    base_path = os.path.join(os.getcwd(), "tmp/test")

    config = ReelsMakerConfig.model_validate(
        {
            "cwd": base_path,
            "subtitles_position": "center,center",
            "threads": 4,
            "text_color": "#ffffff",
            "voice": "en_male_narration",
            "prompt": "Generate a prompt for a sunday morning",
            "sentence": "Today is a fresh start. Reflect on your achievements, rest and rejuvenate, and set new goals for the week ahead. Celebrate your victories, no matter how small, and take time to relax and recharge. Embrace this day with positivity and gratitude.",
            "background_audio_url": "",
            "background_music_path": f"{base_path}/background.mp3",
            "video_paths": [
                f"{base_path}/video1.mp4",
                f"{base_path}/video2.mp4",
            ],
        }
    )
    reels_maker = ReelsMaker(config)
    video_path = await reels_maker.start()
    return video_path
