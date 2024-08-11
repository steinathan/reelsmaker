import os
import uuid
from datetime import timedelta
from pathlib import Path

import srt_equalizer
from loguru import logger
from moviepy.audio.io.AudioFileClip import AudioFileClip
from pydantic import BaseModel


class SubtitleConfig(BaseModel):
    cwd: str
    max_chars: int = 15


class SubtitleGenerator:
    def __init__(self, cwd):
        self.config = SubtitleConfig(cwd=cwd)

    async def wordify(self, srt_path: str, max_chars) -> None:
        """Wordify the srt file, each line is a word

        Example:
        --------------
        1
        00:00:00,000 --> 00:00:00,333
        Imagine

        2
        00:00:00,333 --> 00:00:00,762
        waking up

        3
        00:00:00,762 --> 00:00:01,143
        each day
        ----------------
        """

        srt_equalizer.equalize_srt_file(srt_path, srt_path, max_chars)

    async def generate_subtitles(
        self,
        final_audio_path: str,
        audio_clips: list[AudioFileClip],
        sentences: list[str],
        voice: str | None = None,
    ) -> str:
        logger.info("Generating subtitles...")

        basedir = os.path.join(self.config.cwd, "subtitles")
        os.makedirs(basedir, exist_ok=True)

        subtitles_path = Path(basedir, f"{uuid.uuid4()}.srt")

        subtitles = await self.locally_generate_subtitles(
            sentences=sentences, audio_clips=audio_clips
        )
        with open(subtitles_path, "w+") as file:
            file.write(subtitles)

        await self.wordify(
            srt_path=subtitles_path.as_posix(), max_chars=self.config.max_chars
        )
        return subtitles_path.as_posix()

    async def locally_generate_subtitles(
        self, sentences: list[str], audio_clips: list[AudioFileClip]
    ) -> str:
        """
        Generates subtitles from a given audio file and returns the path to the subtitles.

        Args:
            sentences (List[str]): all the sentences said out loud in the audio clips
            audio_clips (List[AudioFileClip]): all the individual audio clips which will make up the final audio track
        Returns:
            str: The generated subtitles
        """

        logger.debug("using local subtitle generation...")

        def convert_to_srt_time_format(total_seconds):
            # Convert total seconds to the SRT time format: HH:MM:SS,mmm
            if total_seconds == 0:
                return "0:00:00,0"
            return str(timedelta(seconds=total_seconds)).rstrip("0").replace(".", ",")

        start_time = 0
        subtitles = []

        for i, (sentence, audio_clip) in enumerate(
            zip(sentences, audio_clips), start=1
        ):
            duration = audio_clip.duration
            end_time = start_time + duration

            # Format: subtitle index, start time --> end time, sentence
            subtitle_entry = f"{i}\n{convert_to_srt_time_format(start_time)} --> {convert_to_srt_time_format(end_time)}\n{sentence}\n"
            subtitles.append(subtitle_entry)

            start_time += duration  # Update start time for the next subtitle

        return "\n".join(subtitles)
