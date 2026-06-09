from __future__ import annotations

import argparse
import json

from app.agents.hallucination import score_hallucination


def score(query: str, answer: str, context: str) -> float:
    del query
    return score_hallucination(answer, context)


def main() -> None:
    parser = argparse.ArgumentParser(description="Score ClinIQ answer grounding against retrieved context.")
    parser.add_argument("--query", required=True)
    parser.add_argument("--answer", required=True)
    parser.add_argument("--context", required=True)
    args = parser.parse_args()
    value = score(args.query, args.answer, args.context)
    print(json.dumps({"hallucination_score": value}))


if __name__ == "__main__":
    main()
