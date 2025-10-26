import yaml
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from config import settings

# Tool support for the orchestration engine
try:
    from tavily import TavilyClient
    tavily_available = True
except ImportError:
    tavily_available = False

class Tool:
    """Base class for tools that can be used by the orchestration engine."""
    def __init__(self, name: str):
        self.name = name
    
    def run(self, query: str) -> Any:
        raise NotImplementedError("Tool must implement run() method")

class TavilyTool(Tool):
    """Tavily search tool for web searches."""
    def __init__(self):
        super().__init__("tavily")
        if tavily_available and settings.TAVILY_API_KEY:
            self.client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        else:
            self.client = None
    
    def run(self, query: str) -> Any:
        if not self.client:
            return {"error": "Tavily tool is not available (missing API key or library)"}
        try:
            results = self.client.search(query=query, search_depth="basic", max_results=5)
            return results
        except Exception as e:
            return {"error": f"Tavily search failed: {str(e)}"}

class ModelProfile(BaseModel):
    model_id: str
    provider: str
    strengths: List[str]
    context_window: int
    cost_per_token: float
    role: Optional[str] = None

class ModelPool:
    def __init__(self, config_path: str = settings.MODEL_CONFIG_PATH):
        self._models: Dict[str, ModelProfile] = self._load_models_from_config(config_path)
        self._tools: Dict[str, Tool] = self._initialize_tools()
        print(f"ModelPool loaded with {len(self._models)} models: {list(self._models.keys())}")
        print(f"ModelPool loaded with {len(self._tools)} tools: {list(self._tools.keys())}")

    def _initialize_tools(self) -> Dict[str, Tool]:
        """Initialize available tools."""
        tools = {}
        # Add Tavily tool if available
        if tavily_available:
            tools["tavily"] = TavilyTool()
        return tools

    def _load_models_from_config(self, path: str) -> Dict[str, ModelProfile]:
        try:
            with open(path, 'r') as f:
                config = yaml.safe_load(f)
            models = [ModelProfile(**m) for m in config.get('models', [])]
            return {model.model_id: model for model in models}
        except FileNotFoundError:
            return {}
        except Exception as e:
            return {}

    def get_model_profile(self, model_id: str) -> Optional[ModelProfile]:
        return self._models.get(model_id)

    def list_models(self) -> List[ModelProfile]:
        return list(self._models.values())
    
    def get_tool(self, tool_name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self._tools.get(tool_name)

model_pool = ModelPool()