import os
from loguru import logger
import requests


async def search_for_stock_videos(query: str, limit: int, min_dur: int) -> list[str]:
    headers = {
        "Authorization": os.getenv("PEXELS_API_KEY"),
    }

    qurl = f"https://api.pexels.com/videos/search?query={query}&per_page={limit}"

    r = requests.get(qurl, headers=headers)
    response = r.json()

    raw_urls = []
    video_urls = []
    video_res = 0

    try:
        for i in range(limit):
            if response["videos"][i]["duration"] < min_dur:
                continue
            raw_urls = response["videos"][i]["video_files"]
            temp_video_url = ""

            for video in raw_urls:
                if ".com/video-files" in video["link"]:
                    if (video["width"] * video["height"]) > video_res:
                        temp_video_url = video["link"]
                        video_res = video["width"] * video["height"]

            if temp_video_url != "":
                video_urls.append(temp_video_url)

    except Exception as e:
        logger.error(f"Error Searching for video: {e}")

    return video_urls
