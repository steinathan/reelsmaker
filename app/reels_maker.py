import multiprocessing
import os

import aiohttp
from loguru import logger
from moviepy.audio.AudioClip import concatenate_audioclips
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.config import change_settings
from moviepy.editor import VideoFileClip
from pydantic import BaseModel
from typing_extensions import cast

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


class ReelsMakerConfig(BaseModel):
    cwd: str
    subtitles_position: str = "center,center"
    text_color: str | None = "#ffffff"
    voice: str = "en_male_narration"

    prompt: str | None = None
    """ ai prompt to generate sentence """

    sentence: str | None = None
    """ sentence to use instead of prompt """

    background_audio_url: str | None = None
    background_music_path: str | None = None

    video_paths: list[str] = []


class ReelsMaker:
    def __init__(self, config: ReelsMakerConfig):
        self.config = config

        self.cwd = config.cwd
        self.subtitle_generator = SubtitleGenerator(cwd=self.cwd)
        self.video_generator = VideoGenerator(cwd=self.cwd)
        self.syth_generator = SynthGenerator(cwd=self.cwd, voice=config.voice)

        self.sentences: list[str] = []
        self.audio_paths = []
        self.audio_clip_paths = []
        self.final_audio_path = ""

        # Set from client
        self.threads: int = multiprocessing.cpu_count()
        self.subtitles_position = config.subtitles_position
        self.text_color = config.text_color
        self.voice = config.voice
        self.background_music_path = os.path.join(self.cwd, "background.mp3")

        info = {
            "threads": self.threads,
            "text_color": self.text_color,
            "voice": self.voice,
            "background_music_path": self.background_music_path,
            "subtitles_position": self.subtitles_position,
        }
        logger.info(f"Starting Reels Maker with: {info}")

    async def download_audio(self, audio_url) -> str:
        async with aiohttp.ClientSession() as session:
            logger.info(f"Downloading audio from: {audio_url}")
            async with session.get(audio_url) as response:
                with open(
                    os.path.join(self.cwd, os.path.basename(audio_url)), "wb"
                ) as f:
                    f.write(await response.read())
                    return os.path.join(self.cwd, os.path.basename(audio_url))

    async def generate_script(self, prompt: str):
        return self.config.sentence

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

    async def start(self) -> str:
        if self.config.background_audio_url:
            self.background_music_path = await self.download_audio(
                self.config.background_audio_url
            )

        # generate script from prompt
        if self.config.prompt:
            script = await self.generate_script(self.config.prompt)
        elif self.config.sentence:
            script = self.config.sentence
        else:
            raise ValueError("No prompt or sentence provided")

        # split script into sentences
        assert script is not None, "Script should not be None"

        sentences = script.split(". ")
        sentences = list(filter(lambda x: x != "", sentences))
        self.sentences = cast(list[str], sentences)

        video_paths = []
        if self.config.video_paths:
            logger.info("Using video paths from client...")
            video_paths = self.config.video_paths
        else:
            logger.debug("Generating search terms for script...")
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
        return self.final_video_path
