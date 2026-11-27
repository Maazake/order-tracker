import json
import time
from datetime import UTC, datetime

import anthropic

from app.config import settings
from app.llm import estimate_cost_usd
from app.schemas import OrderDraft
from app.services import extract_order_draft

NOW = datetime(2026, 11, 25, tzinfo=UTC)
RUNS = 3
MODELS = ["claude-haiku-5-5"]


class SpyMessages:
    def __init__(self, real_messages):
        self.real_messages = real_messages
        self.input_tokens = 0
        self.output_tokens = 0

    def parse(self, **kwargs):
        response = self.real_messages.parse(**kwargs)
        self.input_tokens += response.usage.input_tokens
        self.output_tokens += response.usage.output_tokens
        return response


class SpyClient:
    def __init__(self, real_client):
        self.messages = SpyMessages(real_client.messages)


if __name__ == "__main__":
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key.get_secret_value())
    for model in MODELS:
        print("===", model)
        spy = SpyClient(client)

        with open("evals/order_draft_cases.json") as file:
            cases = json.load(file)

        passed = 0
        total_seconds = 0
        for case in cases:
            expected = OrderDraft.model_validate(case["expected"])
            for _ in range(RUNS):
                start = time.perf_counter()
                result = extract_order_draft(case["email"], spy, model, NOW)
                total_seconds += time.perf_counter() - start

                if result == expected:
                    passed += 1
                else:
                    print("FAIL |", case["email"])
                    print("     expected:", expected)
                    print("     got:     ", result)

        cost = estimate_cost_usd(
            model,
            spy.messages.input_tokens,
            spy.messages.output_tokens,
        )
        print(f"total cost: ${cost:.4f}")
        print(f"cost per 1000: ${cost / (len(cases) * RUNS) * 1000:.2f}")
        print(f"{passed}/{len(cases) * RUNS} passed")
        print(f"avg time: {total_seconds / (len(cases) * RUNS):.2f} s")
