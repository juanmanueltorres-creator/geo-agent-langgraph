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
