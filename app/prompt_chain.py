from langchain.prompts import ChatPromptTemplate
from langchain_core.globals import set_llm_cache
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from loguru import logger

from langchain.cache import SQLiteCache

set_llm_cache(SQLiteCache(database_path=".llm_cache.db"))


class PromptGenerator:
    def __init__(self):
        tmpl = """
You are a motivational reels narrator, you must generate a motivational quote in a narrative format for the sentence below, and your response must be short and conscience:

[(sentence)]:
{sentence}
 """
        self.model = ChatOpenAI(model="gpt-4o-mini")
        self.prompt = ChatPromptTemplate.from_template(tmpl)
        self.chain = self.prompt | self.model | StrOutputParser()

    async def generate_sentence(self, sentence: str) -> str:
        """generates a sentence from a prompt"""
        logger.debug(f"Generating sentence from prompt: {sentence}")
        return await self.chain.ainvoke({"sentence": sentence})
