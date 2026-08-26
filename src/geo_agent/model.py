import os

from langchain_deepseek import ChatDeepSeek

from .tools.elevation import get_elevation
from .tools.territorial import get_territorial_context
from .tools.weather import get_weather

TOOLS = [get_territorial_context, get_weather, get_elevation]


def build_model():
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is required")

    model = ChatDeepSeek(
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
        api_key=api_key,
        temperature=0,
        timeout=20,
        max_retries=1,
    )
    return model.bind_tools(TOOLS)
