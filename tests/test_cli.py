def test_package_imports():
    import geo_agent

    assert geo_agent.__version__ == "0.1.0"


def test_cli_rejects_empty_question(capsys, monkeypatch):
    from geo_agent.cli import main

    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake")

    assert main([""]) == 2
    assert "Question cannot be empty" in capsys.readouterr().err


def test_cli_rejects_missing_key(capsys, monkeypatch):
    from geo_agent.cli import main

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    assert main(["Analyze Córdoba"]) == 2
    assert "DEEPSEEK_API_KEY is required" in capsys.readouterr().err


def test_cli_prints_tools_and_final_answer(capsys, monkeypatch):
    from geo_agent import cli

    class FakeGraph:
        def invoke(self, state):
            assert state["question"] == "Analyze Córdoba"
            return {
                **state,
                "tool_results": [
                    {
                        "ok": True,
                        "tool": "get_elevation",
                        "data": {"elevation_m": 390.0},
                        "error": None,
                    }
                ],
                "final_answer": "Córdoba is about 390 m above sea level.",
            }

    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake")
    monkeypatch.setattr(cli, "build_graph", lambda: FakeGraph())

    assert cli.main(["Analyze Córdoba"]) == 0
    output = capsys.readouterr().out
    assert "Tools used: get_elevation" in output
    assert "Córdoba is about 390 m above sea level." in output
