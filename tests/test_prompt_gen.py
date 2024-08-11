import json
import pysrt
import pytest

from app.image_gen import generate_image
from app.prompt_gen import PromptGenerator


genarator = PromptGenerator()


@pytest.mark.asyncio
async def test_prompt_gen():
    s = "Create a dark, sinister scene featuring a menacing demon named Ned Schneider. The demon has a terrifying presence, with glowing red eyes, sharp fangs, and dark, shadowy wings. Surround the demon with eerie, twisted surroundings, and depict a woman telling her husband about this evil entity with a sense of dread and fear"
    img_prompt = await genarator.sentence_to_image_prompt(s)
    print(img_prompt)


@pytest.mark.asyncio
async def test_image_gen():
    await generate_image(
        "a dark, sinister scene featuring a menacing demon named Ned Schneider."
    )


@pytest.mark.asyncio
async def test_gen():
    subs = pysrt.open("audio.srt")

    sentences = [sentence.text for sentence in subs]

    image_paths = []
    for sentence in sentences[:10]:
        sentence = sentence.replace('"', "")

        image_prompt = await genarator.sentence_to_image_prompt(sentence)
        generated_image_path = await generate_image(image_prompt)
        image_paths.append(generated_image_path)

    json.dump(image_paths, open("image_paths.json", "w"))

    print("--")
