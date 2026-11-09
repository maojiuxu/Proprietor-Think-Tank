from langchain.chat_models import init_chat_model

from mj.config.config import ConfigVLM

model = None
def get_model_tool(model_name=ConfigVLM.MODEL_DEFAULT_NAME, model_provider="openai"):
    global model
    if model is None:
        model = init_chat_model(
            model=model_name,
            model_provider=model_provider,
            base_url=ConfigVLM.V_MODEL_BASE_URL,
            api_key=ConfigVLM.V_MODEL_API_KEY,
            temperature=ConfigVLM.V_MODEL_TEMPERATURE
        )
    return model