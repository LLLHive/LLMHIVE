from .tavily_client import TavilyClient
from .language_model import LanguageModel
from .summarizer import Summarizer
import os

class ModelPool:
    def __init__(self):
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        self.tools = {}
        self.agents = {}
        self.llms = {}

        if self.tavily_api_key:
            tavily_client = TavilyClient(self.tavily_api_key)
            self.tools["tavily"] = tavily_client
            self.agents["tavily"] = tavily_client
        
        if self.openai_api_key:
            # Using a general-purpose LLM for summarization
            general_llm = LanguageModel(self.openai_api_key, model="gpt-4o")
            self.llms["gpt-4o"] = general_llm
            self.agents["summarizer"] = Summarizer(llm=general_llm)

    def get_tool(self, tool_name: str):
        return self.tools.get(tool_name)

    def get_agent(self, agent_name: str):
        return self.agents.get(agent_name)

    def get_llm(self, llm_name: str):
        return self.llms.get(llm_name)

model_pool = ModelPool()