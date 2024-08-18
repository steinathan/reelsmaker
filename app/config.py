import os


videos_cache_path = os.path.join(os.getcwd(), "cache/videos_cache")
speech_cache_path = os.path.join(os.getcwd(), "cache/speech_cache")
audios_cache_path = os.path.join(os.getcwd(), "cache/audios_cache")


def ensure_caches():
    os.makedirs(videos_cache_path, exist_ok=True)
    os.makedirs(speech_cache_path, exist_ok=True)
    os.makedirs(audios_cache_path, exist_ok=True)


ensure_caches()
