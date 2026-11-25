import json
import time
from datetime import UTC, datetime

import anthropic

from app.config import settings
from app.schemas import OrderDraft
from app.services import extract_order_draft

NOW = datetime(2026, 11, 25, tzinfo=UTC)
RUNS = 3

if __name__ == "__main__":
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key.get_secret_value())

    with open("evals/order_draft_cases.json") as file:
        cases = json.load(file)

    passed = 0
    total_seconds = 0
    for case in cases:
        expected = OrderDraft.model_validate(case["expected"])
        for _ in range(RUNS):
            start = time.perf_counter()
            result = extract_order_draft(case["email"], client, NOW)
            total_seconds += time.perf_counter() - start

            if result == expected:
                passed += 1
                print("PASS |", case["email"])
            else:
                print("FAIL |", case["email"])
                print("     expected:", expected)
                print("     got:     ", result)

    print(f"{passed}/{len(cases) * RUNS} passed")
    print(f"avg time: {total_seconds / (len(cases) * RUNS):.2f} s")
