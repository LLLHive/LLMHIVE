import yaml
from pydantic import BaseModel
from typing import List, Optional, Dict
from config import settings

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
        print(f"ModelPool loaded with {len(self._models)} models: {list(self._models.keys())}")

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

model_pool = ModelPool()