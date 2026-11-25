import json
from datetime import UTC, datetime

import anthropic

from app.config import settings
from app.schemas import OrderDraft
from app.services import extract_order_draft

NOW = datetime(2026, 11, 25, tzinfo=UTC)


if __name__ == "__main__":
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key.get_secret_value())

    with open("evals/order_draft_cases.json") as file:
        cases = json.load(file)

    passed = 0
    for case in cases:
        expected = OrderDraft.model_validate(case["expected"])
        result = extract_order_draft(case["email"], client, NOW)

        if result == expected:
            passed += 1
            print("PASS |", case["email"])
        else:
            print("FAIL |", case["email"])
            print("     expected:", expected)
            print("     got:     ", result)

    print(f"{passed}/{5} passed")  # ile było wszystkich przypadków?
