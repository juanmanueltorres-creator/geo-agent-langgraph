from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from .tools.common import ToolResult


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    question: str
    tool_results: list[ToolResult]
    errors: list[str]
    retry_count: int
    final_answer: str | None
