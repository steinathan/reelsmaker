import asyncio
import multiprocessing
import os
import typing

from loguru import logger
from moviepy.audio.AudioClip import concatenate_audioclips
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.config import change_settings
from moviepy.editor import VideoFileClip

from app.subtitle_gen import SubtitleGenerator
from app.synth_gen import SynthGenerator
from app.video_gen import VideoGenerator

"""
text input
- generate script from text
- generate search terms from script
- for each search term, download video
- split sentences into chunks

Search for videos

 """
change_settings({"IMAGEMAGICK_BINARY": "/tmp/magick"})


class ReelsMaker:
    def __init__(self):
        self.cwd = "tmp"
        self.subtitle_generator = SubtitleGenerator(cwd=self.cwd)
        self.video_generator = VideoGenerator(cwd=self.cwd)
        self.syth_generator = SynthGenerator(cwd=self.cwd)

        self.sentences: list[str] = []
        self.audio_paths = []
        self.audio_clip_paths = []
        self.final_audio_path = ""

        # Set from client
        self.subtitles_position = "center,center"
        self.threads: int = multiprocessing.cpu_count()
        self.text_color = "#ffffff"
        self.voice = "en_male_narration"
        self.background_music_path = os.path.join(self.cwd, "background.mp3")

        info = {
            "threads": self.threads,
            "text_color": self.text_color,
            "voice": self.voice,
            "background_music_path": self.background_music_path,
            "subtitles_position": self.subtitles_position,
        }
        logger.info(f"Starting Reels Maker with: {info}")

    async def generate_script(self, text):
        return """ Embrace this Monday with the energy of a new beginning. Life is a series of fresh starts, and each new week brings an opportunity to write a new chapter. Let today be a reminder that every sunrise is a chance to shine brighter, work harder, and move closer to your dreams. Don’t be afraid to take bold steps and challenge yourself; growth happens outside of your comfort zone. Remember, every step forward, no matter how small, is progress. So, seize the day with positivity and determination, and make this week your masterpiece. """

    async def generate_search_terms(self, script):
        logger.debug("Generating search terms for script...")
        return ["life", "canvas", "waiting", "brush", "unleash"]

    async def synth_text(self, text: str) -> str:
        return await self.syth_generator.generate_audio(text)

    async def generate_subtitles(self) -> str:
        return await self.subtitle_generator.generate_subtitles(
            sentences=self.sentences,
            final_audio_path=self.final_audio_path,
            audio_clips=self.audio_clip_paths,
        )

    async def start(self):
        # generate script from text
        script = await self.generate_script("Life is like a blank canvas")

        # split script into sentences
        sentences = script.split(". ")
        sentences = list(filter(lambda x: x != "", sentences))
        self.sentences = typing.cast(list[str], sentences)

        video_paths = []
        search_terms = await self.generate_search_terms(script=script)
        for search_term in search_terms:
            video_path = await self.video_generator.get_video_url(
                search_term=search_term
            )
            video_paths.append(video_path)

        self.audio_clip_paths: list[AudioFileClip] = []

        # for each sentence, generate audio
        for sentence in self.sentences:
            audio_path = await self.synth_text(sentence)
            self.audio_clip_paths.append(AudioFileClip(audio_path))

        # combine all TTS files using moviepy
        self.final_audio_path = os.path.join(self.cwd, "master__audio.mp3")

        final_audio = concatenate_audioclips(self.audio_clip_paths)
        final_audio.write_audiofile(self.final_audio_path)

        # get subtitles from script
        subtitles_path = await self.generate_subtitles()

        # concatenate videos
        temp_audio = AudioFileClip(self.final_audio_path)
        combined_video_path = await self.video_generator.combine_videos(
            video_paths=video_paths,
            max_duration=temp_audio.duration,
            max_clip_duration=5,
            threads=self.threads,
        )

        # generate video
        self.final_video_path = await self.video_generator.generate_video(
            combined_video_path=combined_video_path,
            tts_path=self.final_audio_path,
            subtitles_path=subtitles_path,
            threads=self.threads,
            subtitles_position=self.subtitles_position,
            text_color=self.text_color,
        )

        video_clip = VideoFileClip(filename=self.final_video_path)

        if self.background_music_path:
            video_clip = await self.video_generator.add_background_music(
                video_clip=video_clip, song_path=self.background_music_path
            )
        else:
            logger.warning("Skipping background music because its not provided")

        video_clip.write_videofile(
            os.path.join(self.cwd, "master__final__video.mp4"), threads=self.threads
        )

        logger.info((f"Final video: {self.final_video_path}"))
        logger.info("video generated successfully!")


async def main():
    reels_maker = ReelsMaker()
    await reels_maker.start()


if __name__ == "__main__":
    asyncio.run(main())
