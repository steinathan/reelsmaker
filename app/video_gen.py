import random
import uuid
from pathlib import Path

from loguru import logger
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.editor import VideoFileClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.video.compositing.concatenate import concatenate_videoclips
from moviepy.video.tools.subtitles import SubtitlesClip
from moviepy.video.VideoClip import TextClip
from moviepy.audio.AudioClip import CompositeAudioClip
from moviepy.video import fx


class VideoGenerator:
    def __init__(
        self,
        cwd,
        fontsize: int = 150,
        stroke_color: str = "black",
        text_color: str = "white",
        stroke_width: int = 5,
    ):
        self.cwd = cwd
        self.fontsize = fontsize
        self.text_color = text_color
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width

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
                tot_dur += clip.duration
                logger.debug(f"Total duration after adding clip: {tot_dur}")

        final_clip = concatenate_videoclips(clips)
        final_clip = final_clip.with_fps(30)
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
        text_color: str | None = None,
    ) -> str:
        def generator(txt):
            return TextClip(
                text=txt,
                font="fonts/bold_font.ttf",
                font_size=self.fontsize,
                color=text_color or self.text_color,
                stroke_color=self.stroke_color,
                stroke_width=self.stroke_width,
                method="label",
                bg_color="yellow",
            )

        horizontal_subtitles_position, vertical_subtitles_position = (
            subtitles_position.split(",")
        )

        subtitles = SubtitlesClip(
            subtitles=subtitles_path, make_textclip=generator, encoding="utf-8"
        )
        result = CompositeVideoClip(
            [
                VideoFileClip(combined_video_path),
                subtitles.with_position(
                    (horizontal_subtitles_position, vertical_subtitles_position)
                ),
            ]
        )

        audio = AudioFileClip(tts_path)
        result = result.with_audio(audio)

        output_path = (Path(self.cwd) / "master__video.mp4").as_posix()
        result.write_videofile(output_path, threads=threads)

        return output_path

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
