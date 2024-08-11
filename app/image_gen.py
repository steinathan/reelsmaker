import re
from httpx import request
import httpx
from loguru import logger


def to_snake_case(string):
    string = (
        re.sub(r"(?<=[a-z])(?=[A-Z])|[^a-zA-Z]", " ", string).strip().replace(" ", "_")
    )
    return "".join(string.lower())


async def generate_image(prompt: str) -> str:
    url = "https://image.pollinations.ai/prompt"
    url = f"{url}/{prompt}"

    logger.debug(f"Generating image from prompt: {prompt}")

    timeout = httpx.Timeout(30.0)
    response = request("GET", url, timeout=timeout)

    fname = to_snake_case(prompt) + ".jpg"
    with open(fname, "wb") as f:
        f.write(response.content)

    return fname
