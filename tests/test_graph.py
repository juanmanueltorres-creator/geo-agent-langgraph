from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from geo_agent.graph import build_graph


def initial_state():
    return {
        "messages": [],
        "question": "Analyze Córdoba",
        "tool_results": [],
        "errors": [],
        "retry_count": 0,
        "final_answer": None,
    }


class FinalModel:
    def __init__(self):
        self.seen_messages = None

    def invoke(self, messages):
        self.seen_messages = list(messages)
        return AIMessage(content="Grounded final answer")


def test_graph_finishes_without_tools_and_preserves_initial_context():
    model = FinalModel()

    result = build_graph(model=model, tool_map={}).invoke(initial_state())

    assert result["final_answer"] == "Grounded final answer"
    assert isinstance(model.seen_messages[0], SystemMessage)
    assert isinstance(model.seen_messages[1], HumanMessage)
    assert model.seen_messages[1].content == "Analyze Córdoba"
    assert isinstance(result["messages"][0], SystemMessage)
    assert isinstance(result["messages"][1], HumanMessage)


class ToolThenFinalModel:
    def __init__(self):
        self.calls = 0
        self.second_messages = None

    def invoke(self, messages):
        self.calls += 1
        if self.calls == 1:
            return AIMessage(
                content="",
                tool_calls=[{
                    "name": "get_elevation",
                    "args": {"latitude": -31.42, "longitude": -64.19},
                    "id": "call-elevation-1",
                    "type": "tool_call",
                }],
            )
        self.second_messages = list(messages)
        return AIMessage(content="Elevation retrieved and validated")


def test_graph_executes_tool_validates_and_returns_to_model():
    model = ToolThenFinalModel()
    tools = {
        "get_elevation": lambda latitude, longitude: {
            "ok": True,
            "tool": "get_elevation",
            "data": {"elevation_m": 390.0},
            "error": None,
        }
    }

    result = build_graph(model=model, tool_map=tools).invoke(initial_state())

    assert result["tool_results"][0]["data"]["elevation_m"] == 390.0
    assert result["final_answer"] == "Elevation retrieved and validated"
    assert model.calls == 2
    assert any(isinstance(message, ToolMessage) for message in model.second_messages)


class AlwaysToolModel:
    def __init__(self):
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        return AIMessage(
            content="",
            tool_calls=[{
                "name": "get_weather",
                "args": {"latitude": -31.42, "longitude": -64.19},
                "id": f"weather-call-{self.calls}",
                "type": "tool_call",
            }],
        )


def test_graph_stops_after_exactly_one_retry_even_if_model_keeps_requesting_tools():
    model = AlwaysToolModel()
    tools = {
        "get_weather": lambda latitude, longitude: {
            "ok": False,
            "tool": "get_weather",
            "data": None,
            "error": "provider unavailable",
        }
    }

    result = build_graph(model=model, tool_map=tools).invoke(initial_state())

    assert result["retry_count"] == 1
    assert len(result["tool_results"]) == 2
    assert model.calls == 2
    assert result["final_answer"].startswith("Partial result:")


class FinalInsteadOfRetryModel:
    def __init__(self):
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        if self.calls == 1:
            return AIMessage(
                content="",
                tool_calls=[{
                    "name": "get_weather",
                    "args": {"latitude": -31.42, "longitude": -64.19},
                    "id": "weather-first",
                    "type": "tool_call",
                }],
            )
        return AIMessage(content="I will answer without retrying the failed source")


def test_graph_forces_partial_answer_if_retry_prompt_does_not_produce_a_new_tool_call():
    tools = {
        "get_weather": lambda latitude, longitude: {
            "ok": False,
            "tool": "get_weather",
            "data": None,
            "error": "provider unavailable",
        }
    }

    result = build_graph(model=FinalInsteadOfRetryModel(), tool_map=tools).invoke(initial_state())

    assert result["retry_count"] == 1
    assert result["final_answer"].startswith("Partial result:")
