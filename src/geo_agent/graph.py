import json
from collections.abc import Mapping
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph

from .model import TOOLS, build_model
from .state import AgentState
from .tools.common import failure
from .validation import validate_tool_result

SYSTEM_PROMPT = (
    "You are a geospatial analysis agent. Use the provided tools for factual measurements. "
    "Never invent coordinates, weather, elevation, or administrative context. "
    "Use territorial context first when a place name must be resolved to coordinates. "
    "You may call multiple tools when appropriate, but only with arguments supported by "
    "the user request or prior tool results. If data is unavailable, state that clearly."
)


def _default_tool_map() -> dict[str, Any]:
    return {item.name: item for item in TOOLS}


def _latest_tool_batch(state: AgentState) -> list[dict[str, Any]]:
    for message in reversed(state["messages"]):
        if isinstance(message, AIMessage) and message.tool_calls:
            count = len(message.tool_calls)
            return state["tool_results"][-count:]
    return []


def _batch_has_invalid_result(state: AgentState) -> bool:
    batch = _latest_tool_batch(state)
    return bool(batch) and any(not validate_tool_result(item)[0] for item in batch)


def build_graph(model=None, tool_map: Mapping[str, Any] | None = None):
    bound_model = model or build_model()
    tools = dict(_default_tool_map() if tool_map is None else tool_map)

    def agent_node(state: AgentState):
        current_messages = list(state["messages"])
        initial_messages = not current_messages
        if initial_messages:
            current_messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=state["question"]),
            ]

        response = bound_model.invoke(current_messages)
        messages_to_add = current_messages + [response] if initial_messages else [response]
        update: dict[str, Any] = {"messages": messages_to_add}
        if isinstance(response, AIMessage) and not response.tool_calls:
            update["final_answer"] = str(response.content)
        return update

    def tool_node(state: AgentState):
        last = state["messages"][-1]
        results = []
        tool_messages = []

        for call in getattr(last, "tool_calls", []):
            name = call["name"]
            target = tools.get(name)
            if target is None:
                result = failure(name, f"Unknown tool requested: {name}")
            else:
                try:
                    if hasattr(target, "invoke"):
                        result = target.invoke(call["args"])
                    else:
                        result = target(**call["args"])
                except Exception as exc:  # defensive boundary around tool execution
                    result = failure(name, f"Tool execution failed: {exc}")

            if not isinstance(result, dict):
                result = failure(name, "Tool returned an invalid result type")

            results.append(result)
            tool_messages.append(
                ToolMessage(
                    content=json.dumps(result, ensure_ascii=False, default=str),
                    tool_call_id=call["id"],
                )
            )

        return {
            "messages": tool_messages,
            "tool_results": state["tool_results"] + results,
        }

    def validate_node(state: AgentState):
        errors = list(state["errors"])
        for result in _latest_tool_batch(state):
            valid, error = validate_tool_result(result)
            if not valid and error:
                errors.append(error)
        return {"errors": errors}

    def retry_node(state: AgentState):
        return {
            "retry_count": state["retry_count"] + 1,
            "messages": [
                HumanMessage(
                    content=(
                        "A tool call failed validation. Retry the failed data retrieval once "
                        "using the available context. Do not invent missing values."
                    )
                )
            ],
        }

    def partial_node(state: AgentState):
        successful = [item for item in state["tool_results"] if item.get("ok")]
        names = ", ".join(dict.fromkeys(item["tool"] for item in successful)) or "none"
        missing = state["errors"][-1] if state["errors"] else "unknown provider failure"
        return {
            "final_answer": (
                f"Partial result: successful tools: {names}. "
                f"Missing data: {missing}."
            )
        }

    def route_after_agent(state: AgentState):
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools"
        if state["retry_count"] > 0 and _batch_has_invalid_result(state):
            return "partial"
        return END

    def route_after_validate(state: AgentState):
        if not _batch_has_invalid_result(state):
            return "agent"
        return "retry" if state["retry_count"] == 0 else "partial"

    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    workflow.add_node("validate", validate_node)
    workflow.add_node("retry", retry_node)
    workflow.add_node("partial", partial_node)

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", route_after_agent)
    workflow.add_edge("tools", "validate")
    workflow.add_conditional_edges("validate", route_after_validate)
    workflow.add_edge("retry", "agent")
    workflow.add_edge("partial", END)

    return workflow.compile()
