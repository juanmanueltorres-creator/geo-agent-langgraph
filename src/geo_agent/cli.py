import argparse
import os
import sys

from dotenv import load_dotenv

from .graph import build_graph


def main(argv: list[str] | None = None) -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Run a grounded geospatial AI agent.")
    parser.add_argument("question")
    args = parser.parse_args(argv)

    question = args.question.strip()
    if not question:
        print("Question cannot be empty", file=sys.stderr)
        return 2

    if not os.getenv("DEEPSEEK_API_KEY"):
        print("DEEPSEEK_API_KEY is required", file=sys.stderr)
        return 2

    result = build_graph().invoke(
        {
            "messages": [],
            "question": question,
            "tool_results": [],
            "errors": [],
            "retry_count": 0,
            "final_answer": None,
        }
    )

    tools = [item["tool"] for item in result.get("tool_results", [])]
    if tools:
        print("Tools used: " + ", ".join(tools))

    print(result.get("final_answer") or "No final answer was produced.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
