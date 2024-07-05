import asyncio
import multiprocessing
import os
import random
import typing
import uuid
from datetime import timedelta
from pathlib import Path

import srt_equalizer
from loguru import logger
from moviepy.audio.AudioClip import CompositeAudioClip, concatenate_audioclips
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.config import change_settings
from moviepy.editor import VideoFileClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.video.compositing.concatenate import concatenate_videoclips
from moviepy.video.fx.all import blackwhite, crop  # type: ignore
from moviepy.video.tools.subtitles import SubtitlesClip
from moviepy.video.VideoClip import TextClip

"""
text input
- generate script from text
- generate search terms from script

- for each search term, download video

- split sentences into chunks


Search for videos

 """
change_settings({"IMAGEMAGICK_BINARY": "/tmp/magick"})


class SubtitleGenerator:
    def __init__(self, cwd):
        self.cwd = cwd

    async def equalize_subtitles(self, srt_path: str, max_chars: int = 10) -> None:
        srt_equalizer.equalize_srt_file(srt_path, srt_path, max_chars)

    async def generate_subtitles(
        self,
        final_audio_path: str,
        audio_clips: list[AudioFileClip],
        sentences: list[str],
        voice: str | None = None,
    ) -> str:
        logger.info("Generating subtitles...")

        subtitles_path = Path(self.cwd) / f"subtitles/{uuid.uuid4()}.srt"

        subtitles = await self.locally_generate_subtitles(
            sentences=sentences, audio_clips=audio_clips
        )
        with open(subtitles_path, "w+") as file:
            file.write(subtitles)

        await self.equalize_subtitles(srt_path=subtitles_path.as_posix())
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


class VideoGenerator:
    def __init__(self, cwd):
        self.cwd = cwd

    async def combine_videos(
        self,
        video_paths: list[str],
        max_duration: int,
        max_clip_duration: int,
        threads: int,
    ) -> str:
        video_id = uuid.uuid4()
        combined_video_path = (Path(self.cwd) / f"{video_id}.mp4").as_posix()

        # Required duration of each clip
        req_dur = max_duration / len(video_paths)

        logger.debug("Combining videos...")
        logger.debug(f"Each clip will be maximum {req_dur} seconds long.")

        clips = []
        tot_dur = 0

        while tot_dur < max_duration:
            for video_path in video_paths:
                clip = VideoFileClip(video_path)
                clip = clip.without_audio()
                logger.debug(
                    f"Processing clip: {video_path}, duration: {clip.duration}"
                )

                if (max_duration - tot_dur) < clip.duration:
                    clip = clip.subclip(0, (max_duration - tot_dur))
                elif req_dur < clip.duration:
                    clip = clip.subclip(0, req_dur)
                clip = clip.set_fps(30)

                if round((clip.w / clip.h), 4) < 0.5625:
                    clip = crop(
                        clip,
                        width=clip.w,
                        height=round(clip.w / 0.5625),
                        x_center=clip.w / 2,
                        y_center=clip.h / 2,
                    )
                else:
                    clip = crop(
                        clip,
                        width=round(0.5625 * clip.h),
                        height=clip.h,
                        x_center=clip.w / 2,
                        y_center=clip.h / 2,
                    )
                clip = clip.resize((1080, 1920))

                # apply grayscale effect
                clip = blackwhite(clip)

                if clip.duration > max_clip_duration:
                    clip = clip.subclip(0, max_clip_duration)

                clips.append(clip)
                tot_dur += clip.duration
                logger.debug(f"Total duration after adding clip: {tot_dur}")

        final_clip = concatenate_videoclips(clips)
        final_clip = final_clip.set_fps(30)
        final_clip.write_videofile(combined_video_path, threads=threads)

        return combined_video_path

    async def get_video_url(self, search_term: str) -> str:
        idx = round(random.uniform(1, 3))
        return (Path(self.cwd) / f"segments/{idx}.mp4").as_posix()

    async def generate_video(
        self,
        combined_video_path: str,
        tts_path: str,
        subtitles_path: str,
        threads: int,
        subtitles_position: str,
        text_color: str,
    ) -> str:
        def generator(txt):
            return TextClip(
                txt=txt,
                font="fonts/bold_font.ttf",
                fontsize=100,
                color=text_color,
                stroke_color="black",
                stroke_width=5,
            )

        horizontal_subtitles_position, vertical_subtitles_position = (
            subtitles_position.split(",")
        )

        subtitles = SubtitlesClip(subtitles=subtitles_path, make_textclip=generator)
        result = CompositeVideoClip(
            [
                VideoFileClip(combined_video_path),
                subtitles.set_pos(  # type: ignore
                    (horizontal_subtitles_position, vertical_subtitles_position)
                ),
            ]
        )

        audio = AudioFileClip(tts_path)
        result = result.set_audio(audio)

        output_path = (Path(self.cwd) / "master__video.mp4").as_posix()
        result.write_videofile(output_path, threads=threads)

        return output_path


class ReelsMaker:
    def __init__(self):
        self.cwd = "tmp"
        self.subtitle_generator = SubtitleGenerator(cwd=self.cwd)
        self.video_generator = VideoGenerator(cwd=self.cwd)

        self.sentences: list[str] = []
        self.audio_paths = []
        self.audio_clip_paths = []
        self.final_audio_path = ""

        # Set from client
        self.subtitles_position = "center,center"
        self.threads: int = multiprocessing.cpu_count()
        self.text_color = "#ffffff"
        self.voice = "en_us_010"
        self.background_music_path = os.path.join(self.cwd, "background.mp3")

    async def generate_script(self, text):
        return """ Life is like a blank canvas, patiently waiting for you to seize the brush and unleash your creativity. Every stroke you make, every decision you take, shapes the vibrant image that is your unique existence. """

    async def generate_search_terms(self, script):
        logger.debug("Generating search terms for script...")
        return ["life", "canvas", "waiting", "brush", "unleash"]

    async def synth_text(self, text: str) -> str:
        logger.debug(f"Synthesizing text: {text}")
        import tiktokvoice

        filename = os.path.join(self.cwd, f"{uuid.uuid4()}.mp3")
        tiktokvoice.tts(text, voice=self.voice, filename=filename)
        return filename

    async def __generate_subtitles(self) -> str:
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

        video_paths = [
            "tmp/segments/1.mp4",
            "tmp/segments/2.mp4",
            "tmp/segments/3.mp4",
        ]
        # search_terms = await self.generate_search_terms(script=script)
        # for search_term in search_terms:
        #     video_path = await self.video_generator.get_video_url(
        #         search_term=search_term
        #     )
        #     video_paths.append(video_path)

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
        subtitles_path = await self.__generate_subtitles()

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

        video_clip = VideoFileClip(self.final_video_path)

        if self.background_music_path:
            video_clip = await self.add_background_music(video_clip)
        else:
            logger.warning("Skipping background music because its not provided")

        video_clip.write_videofile(
            os.path.join(self.cwd, "master__final__video.mp4"), threads=self.threads
        )

        logger.info((f"Final video: {self.final_video_path}"))
        logger.info("video generated successfully!")

    async def add_background_music(self, video_clip: VideoFileClip):
        logger.info(f"Adding background music: {self.background_music_path}")
        song_path = self.background_music_path

        # add song to video at 30% volume using moviepy
        original_duration = video_clip.duration
        original_audio = video_clip.audio
        song_clip = AudioFileClip(song_path).set_fps(44100)

        # set the volume of the song to 10% of the original volume
        song_clip = song_clip.volumex(0.1).set_fps(44100)

        # add the song to the video
        comp_audio = CompositeAudioClip([original_audio, song_clip])
        video_clip = video_clip.set_audio(comp_audio)
        video_clip = video_clip.set_fps(30)
        video_clip = video_clip.set_duration(original_duration)
        return video_clip


async def main():
    reels_maker = ReelsMaker()
    await reels_maker.start()


if __name__ == "__main__":
    asyncio.run(main())
