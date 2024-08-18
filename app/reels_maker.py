import asyncio
import multiprocessing
import os
import shutil

import aiohttp
import moviepy.config as moviepy_config
from dotenv import load_dotenv
from loguru import logger
from moviepy.audio.AudioClip import concatenate_audioclips
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.editor import VideoFileClip
from pydantic import BaseModel
from typing_extensions import cast

from app.config import videos_cache_path
from app.prompt_gen import PromptGenerator
from app.subtitle_gen import SubtitleGenerator
from app.synth_gen import SynthConfig, SynthGenerator
from app.utils import split_by_dot_or_newline
from app.utils import search_file
from app.video_gen import VideoGenerator, VideoGeneratorConfig

load_dotenv()

magickpath = os.path.join(os.getcwd(), "bin", "magick")

os.environ["IMAGEMAGICK_BINARY"] = magickpath
moviepy_config.IMAGEMAGICK_BINARY = magickpath

moviepy_config.check()


class ReelsMakerConfig(BaseModel):
    cwd: str
    prompt: str | None = None
    """ ai prompt to generate sentence """

    sentence: str | None = None
    """ sentence to use instead of prompt """

    background_audio_url: str | None = None
    background_music_path: str | None = None

    video_paths: list[str] = []

    video_gen_config: VideoGeneratorConfig = VideoGeneratorConfig()
    """ config for the video generator """

    synth_config: SynthConfig = SynthConfig()
    """ config for the synthesizer """


class ReelsMaker:
    def __init__(self, config: ReelsMakerConfig):
        self.config = config

        self.cwd = config.cwd
        self.subtitle_generator = SubtitleGenerator(cwd=self.cwd)

        self.video_generator = VideoGenerator(self.cwd, config.video_gen_config)
        self.syth_generator = SynthGenerator(self.cwd, config.synth_config)
        self.prompt_generator = PromptGenerator()

        self.sentences: list[str] = []

        self.audio_paths = []
        self.audio_clip_paths = []
        self.final_audio_path = ""

        # Set from client
        self.threads: int = multiprocessing.cpu_count()
        self.background_music_path = self.config.background_music_path

        logger.info(f"Starting Reels Maker with: {self.config.model_dump()}")

    async def download_resource(self, url) -> str:
        filename = os.path.basename(url)
        file_path = os.path.join(self.cwd, filename)
        file_cache_path = search_file(videos_cache_path, filename)
        if file_cache_path:
            shutil.copy2(file_cache_path, file_path)
            logger.info(f"Found resource in cache: {file_cache_path}")
            return file_path

        async with aiohttp.ClientSession() as session:
            logger.info(f"Downloading resource from: {url}")
            async with session.get(url) as response:
                with open(file_path, "wb") as f:
                    f.write(await response.read())
                    logger.debug(f"Downloaded resource from: {url}")

                    # save to cache audios
                    shutil.copy2(file_path, videos_cache_path)
                    return os.path.join(self.cwd, os.path.basename(url))

    async def generate_script(self, sentence: str):
        logger.debug(f"Generating script from prompt: {sentence}")
        sentence = await self.prompt_generator.generate_sentence(sentence)
        return sentence.replace('"', "")

    async def generate_search_terms(self, script, max_hashtags: int = 5):
        logger.debug("Generating search terms for script...")
        response = await self.prompt_generator.generate_hashtags(script)
        tags = [tag.replace("#", "") for tag in response.hashtags]
        if len(tags) > max_hashtags:
            logger.warning(f"Truncated search terms to {max_hashtags} tags")
            tags = tags[:max_hashtags]

        logger.info(f"Generated search terms: {tags}")
        return tags

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
            self.background_music_path = await self.download_resource(
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

        sentences = split_by_dot_or_newline(script)
        sentences = list(filter(lambda x: x != "", sentences))
        self.sentences = cast(list[str], sentences)

        video_paths = []
        if self.config.video_paths:
            logger.info("Using video paths from client...")
            video_paths = self.config.video_paths
        else:
            logger.debug("Generating search terms for script...")
            search_terms = await self.generate_search_terms(
                script=script, max_hashtags=10
            )

            # holds all remote urls
            remote_urls = []

            max_videos = int(os.getenv("MAX_BG_VIDEOS", 2))

            for search_term in search_terms[:max_videos]:
                # search for a related background video
                video_path = await self.video_generator.get_video_url(
                    search_term=search_term
                )
                if not video_path:
                    continue

                remote_urls.append(video_path)

            # download all remote videos at once
            tasks = []
            for url in remote_urls:
                task = asyncio.create_task(self.download_resource(url))
                tasks.append(task)

            local_paths = await asyncio.gather(*tasks)
            video_paths.extend(local_paths)

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
            max_clip_duration=3,
            threads=self.threads,
        )

        # generate video
        self.final_video_path = await self.video_generator.generate_video(
            combined_video_path=combined_video_path,
            tts_path=self.final_audio_path,
            subtitles_path=subtitles_path,
        )

        video_clip = VideoFileClip(filename=self.final_video_path)

        if self.background_music_path:
            video_clip = await self.video_generator.add_background_music(
                video_clip=video_clip, song_path=self.background_music_path
            )
        else:
            logger.warning("Skipping background music because its not provided")

        video_clip = await self.video_generator.add_fade_out(video_clip)

        self.final_video_path = os.path.join(self.cwd, "master__final__video.mp4")
        video_clip.write_videofile(self.final_video_path, threads=self.threads)

        logger.info((f"Final video: {self.final_video_path}"))
        logger.info("video generated successfully!")
        return self.final_video_path
