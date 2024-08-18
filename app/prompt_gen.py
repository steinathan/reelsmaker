from langchain.cache import SQLiteCache
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import ChatPromptTemplate
from langchain_core.globals import set_llm_cache
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from loguru import logger
from pydantic import BaseModel, Field

set_llm_cache(SQLiteCache(database_path=".llm_cache.db"))


class HashtagsSchema(BaseModel):
    """the hashtags response"""

    hashtags: list[str] = Field(description="List of hashtags for the sentence")


class PromptGenerator:
    def __init__(self):
        self.model = ChatOpenAI(model="gpt-4o-mini")

    async def generate_sentence(self, sentence: str) -> str:
        """generates a sentence from a prompt"""

        tmpl = """
You are a motivational reels narrator, you must generate a motivational quote in a narrative format for the sentence below, and your response must be short and conscience:

[(sentence)]:
{sentence}
 """

        prompt = ChatPromptTemplate.from_template(tmpl)

        chain = prompt | self.model | StrOutputParser()

        logger.debug(f"Generating sentence from prompt: {sentence}")
        return await chain.ainvoke({"sentence": sentence})

    async def generate_hashtags(self, sentence: str) -> HashtagsSchema:
        """generates hashtags from a sentence"""

        system_template = """
generate pexels.com hashtags keywords for the sentence below, the hashtags must be short and concise and will be used to query the api:

{format_instructions}

[(sentence)]:
{sentence}
 """

        parser = PydanticOutputParser(pydantic_object=HashtagsSchema)
        prompt = ChatPromptTemplate.from_messages(
            messages=[("system", system_template), ("user", "{sentence}")]
        )
        prompt = prompt.partial(format_instructions=parser.get_format_instructions())

        chain = prompt | self.model | parser

        logger.debug(f"Generating sentence from prompt: {sentence}")
        return await chain.ainvoke({"sentence": sentence})

    async def sentence_to_image_prompt(self, sentence: str) -> str:
        """generates an image prompt from a sentence"""

        tmpl = """
You are an AI image prompt generator, I will give you a sentence and you must generate the prompt to be used in an AI image generator to output images - you response must be brief, you must not include explanations whatsoever only the prompt

[(sentence)]:
{sentence}
 """
        prompt = ChatPromptTemplate.from_template(tmpl)
        chain = prompt | self.model | StrOutputParser()

        logger.debug(f"Generating sentence from prompt: {sentence}")
        return await chain.ainvoke({"sentence": sentence})
