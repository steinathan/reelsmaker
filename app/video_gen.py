import multiprocessing
import os
import random
import uuid
from pathlib import Path

from loguru import logger
from moviepy import ImageClip
from moviepy.audio.AudioClip import CompositeAudioClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.editor import VideoFileClip
from moviepy.video import fx
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.video.compositing.concatenate import concatenate_videoclips
from moviepy.video.tools.subtitles import SubtitlesClip
from moviepy.video.VideoClip import TextClip
from pydantic import BaseModel
from app.pexel import search_for_stock_videos


class VideoGeneratorConfig(BaseModel):
    fontsize: int = 100
    stroke_color: str = "black"
    text_color: str = "white"
    stroke_width: int = 5
    font_path: str = "fonts/bold_font.ttf"
    bg_color: str | None = None
    subtitles_position: str = "center,center"
    threads: int = multiprocessing.cpu_count()
    watermark_path: str | None = None


class VideoGenerator:
    def __init__(
        self,
        cwd: str,
        config: VideoGeneratorConfig,
    ):
        self.config = config
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
                clip = VideoFileClip(video_path).without_audio()
                logger.debug(
                    f"Processing clip: {video_path}, duration: {clip.duration}"
                )

                if (max_duration - tot_dur) < clip.duration:
                    clip = clip.subclip(0, (max_duration - tot_dur))
                elif req_dur < clip.duration:
                    clip = clip.subclip(0, req_dur)
                clip = clip.with_fps(30)

                if round((clip.w / clip.h), 4) < 0.5625:
                    clip = fx.crop(
                        clip,
                        width=clip.w,
                        height=round(clip.w / 0.5625),
                        x_center=clip.w / 2,
                        y_center=clip.h / 2,
                    )
                else:
                    clip = fx.crop(
                        clip,
                        width=round(0.5625 * clip.h),
                        height=clip.h,
                        x_center=clip.w / 2,
                        y_center=clip.h / 2,
                    )
                clip = clip.resize((1080, 1920))

                # apply grayscale effect
                clip = fx.blackwhite(clip)

                if clip.duration > max_clip_duration:
                    clip = clip.subclip(0, max_clip_duration)

                clips.append(clip)

                self.close_clip(clip)
                tot_dur += clip.duration
                logger.debug(f"Total duration after adding clip: {tot_dur}")

        final_clip = concatenate_videoclips(clips=clips, method="compose")
        final_clip = final_clip.with_fps(30)
        final_clip.write_videofile(combined_video_path, threads=threads)

        return combined_video_path

    async def get_video_url(self, search_term: str) -> str | None:
        try:
            urls = await search_for_stock_videos(
                limit=2,
                min_dur=10,
                query=search_term,
            )
            return urls[0] if len(urls) > 0 else None
        except Exception as e:
            logger.error(f"Consistency Violation: {e}")

        return None

    async def generate_video(
        self,
        combined_video_path: str,
        tts_path: str,
        subtitles_path: str,
    ) -> str:
        def generator(txt) -> TextClip:
            textclip_kwargs = {
                "font_size": self.config.fontsize,
                "color": self.config.text_color,
                "stroke_color": self.config.stroke_color,
                "stroke_width": self.config.stroke_width,
                "bg_color": self.config.bg_color,
            }

            # remove keys with "none"
            for k, v in textclip_kwargs.items():
                if not v:
                    del textclip_kwargs[k]

            textclip = TextClip(
                text=txt,
                font="fonts/bold_font.ttf",
                method="label",
                **textclip_kwargs,
            )

            return textclip

        horizontal_subtitles_position, vertical_subtitles_position = (
            self.config.subtitles_position.split(",")
        )

        subtitles = SubtitlesClip(
            subtitles=subtitles_path, make_textclip=generator, encoding="utf-8"
        )

        subtitles_clip = subtitles.with_position(
            (horizontal_subtitles_position, vertical_subtitles_position)
        )

        self.video_clip = VideoFileClip(combined_video_path)

        clips = [self.video_clip, subtitles_clip]

        if self.config.watermark_path:
            watermark_clip = self.__get_watermark_clip()
            if watermark_clip:
                logger.debug(f"added watermark: {self.config.watermark_path}")
                clips.append(self.__get_watermark_clip())

        result = CompositeVideoClip(clips=clips)

        audio = AudioFileClip(tts_path)
        result = result.with_audio(audio)

        output_path = (Path(self.cwd) / "master__video.mp4").as_posix()
        result.write_videofile(output_path, threads=self.config.threads)

        return output_path

    def close_clip(self, clip: VideoFileClip):
        try:
            clip.close()
        except Exception as e:
            logger.exception(f"Error in close_clip(): {e}")

    async def add_background_music(self, video_clip: VideoFileClip, song_path: str):
        logger.info(f"Adding background music: {song_path}")

        original_duration = video_clip.duration
        original_audio = video_clip.audio
        song_clip = AudioFileClip(song_path).with_fps(44100)

        # set the volume of the song to 10% of the original volume
        song_clip = song_clip.subclip().multiply_volume(0.2)

        # add the song to the video
        comp_audio = CompositeAudioClip([original_audio, song_clip])
        video_clip = video_clip.with_audio(comp_audio)
        video_clip = video_clip.with_fps(30)
        video_clip = video_clip.with_duration(original_duration)
        return video_clip

    async def add_fade_out(self, video_clip: VideoFileClip) -> VideoFileClip:
        """Adds a fade out to the end of the video but let the audio continue playing."""
        return fx.fadeout(video_clip, 3)

    def __get_watermark_clip(self):
        if not self.config.watermark_path:
            logger.warning("Skipping watermark because its not provided")
            return None

        assert self.video_clip is not None, "Video is not loaded"

        watermark = ImageClip(self.config.watermark_path)
        watermark = watermark.with_duration(self.video_clip.duration)
        watermark = watermark.with_position(("right", "bottom"))
        watermark = watermark.margin(right=8, top=8, bottom=8, opacity=0)
        watermark = watermark.resize(height=50)

        return watermark
