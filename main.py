import asyncio
from app.reels_maker import ReelsMaker, ReelsMakerConfig


async def main():
    config = ReelsMakerConfig.model_validate(
        {
            "cwd": "/home/navicstein/Projects/automovie/tmp/3e760c2b-73c5-4b5c-b5fa-a0bd756b370e",
            "subtitles_position": "center,center",
            "text_color": "#ffffff",
            "voice": "en_male_narration",
            "prompt": "",
            "background_audio_url": "",
            "background_music_path": "/home/navicstein/Projects/automovie/tmp/3e760c2b-73c5-4b5c-b5fa-a0bd756b370e/background.mp3",
            "video_paths": [
                "/home/navicstein/Projects/automovie/tmp/3e760c2b-73c5-4b5c-b5fa-a0bd756b370e/Screenshare - 2023-05-19 10_33_01 PM.mp4",
                "/home/navicstein/Projects/automovie/tmp/3e760c2b-73c5-4b5c-b5fa-a0bd756b370e/Screenshare - 2023-05-19 10_30_11 PM.mp4",
            ],
        }
    )
    reels_maker = ReelsMaker(config)
    video_path = await reels_maker.start()
    return video_path


if __name__ == "__main__":
    asyncio.run(main())
