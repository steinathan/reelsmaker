import asyncio
import os
from uuid import uuid4

from loguru import logger
import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile
from app.reels_maker import ReelsMaker, ReelsMakerConfig


if "queue" not in st.session_state:
    st.session_state["queue"] = {}

queue: dict[str, ReelsMakerConfig] = st.session_state["queue"]


async def download_to_path(dest: str, buff: UploadedFile) -> str:
    with open(dest, "wb") as f:
        f.write(buff.getbuffer())
    return dest


async def main():
    st.title("AI Reels Story Maker")
    st.write("Auto generate AI Reels Video Story from simple prompts")
    st.divider()

    prompt = st.text_area(
        label="Enter your prompt",
        placeholder="A motivation quote about life & pleasure",
        height=100,
    )

    sentence = st.text_area(
        label="Enter your quote",
        placeholder="Nothing is impossible. The word itself says 'I'm possible!, Champions keep playing until they get it right, You are never too old to set another goal or to dream a new dream.",
        height=100,
    )

    st.write("Choose background videos")
    upload_video_tab, auto_video_tab = st.tabs(["Upload Videos", "Auto Add video"])

    with auto_video_tab:
        st.warning("Sorry, this feature is not available yet")
        st.write(
            "We'll automatically download background videos related to your prompt, usefull when you don't have a background video"
        )

    with upload_video_tab:
        uploaded_videos = st.file_uploader(
            "Upload a background videos",
            type=["mp4", "webm"],
            accept_multiple_files=True,
        )

    st.write("Choose a background audio")
    upload_audio_tab, audio_url_tab = st.tabs(["Upload audio", "Enter Audio Url"])

    with upload_audio_tab:
        uploaded_audio = st.file_uploader(
            "Upload a background audio", type=["mp3", "webm"]
        )

    with audio_url_tab:
        st.warning("Sorry, this feature is not available yet")
        background_audio_url = st.text_input(
            "Enter a background audio URL", placeholder="Enter URL"
        )

    voice = st.selectbox("Choose a voice", ["en_male_narration", "en_us_001"])

    # Subtitles color
    color = st.selectbox("Subtitles color", ["#ffffff", "#000000"])

    # Subtitles position
    subtitles_position = st.selectbox("Subtitles position", ["center,center"])

    submitted = st.button("Generate Reels", use_container_width=True, type="primary")

    if submitted:
        queue_id = str(uuid4())

        cwd = os.path.join(os.getcwd(), "tmp", queue_id)
        os.makedirs(cwd, exist_ok=True)

        # create config
        config = ReelsMakerConfig(
            background_audio_url=background_audio_url,
            cwd=cwd,
            prompt=prompt,
            sentence=sentence,
            subtitles_position=subtitles_position or "center,center",
            text_color=color or "#ffffff",
            voice=voice or "en_male_narration",
        )

        # read all uploaded files and save in a path
        if uploaded_videos:
            config.video_paths = [
                await download_to_path(dest=os.path.join(config.cwd, p.name), buff=p)
                for p in uploaded_videos
            ]
        else:
            st.error("please upload 1 or more videos")
            return

        # read uploaded file and save in a path
        if uploaded_audio:
            config.background_music_path = await download_to_path(
                dest=os.path.join(config.cwd, "background.mp3"), buff=uploaded_audio
            )
        else:
            st.error("No audio uploaded")
            return

        print(f"starting reels maker: {config.model_dump_json()}")

        with st.spinner("Generating reels, wait for it..."):
            try:
                if len(queue.items()) > 1:
                    raise Exception("queue is full - someone else is generating reels")

                logger.debug("Added to queue")
                queue[queue_id] = config

                reels_maker = ReelsMaker(config)
                video_path = await reels_maker.start()
                st.balloons()
                st.video(video_path, autoplay=True)
                st.download_button("Download Reels", video_path, file_name="reels.mp4")
            except Exception as e:
                del queue[queue_id]
                logger.exception(f"removed from queue: {queue_id}: -> {e}")
                st.error(e)


asyncio.run(main())
