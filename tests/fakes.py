from dataclasses import dataclass

import anthropic
import httpx2

from app.schemas import OrderDraft


@dataclass
class FakeBlock:
    type: str
    text: str


@dataclass
class FakeUsage:
    input_tokens: int
    output_tokens: int


@dataclass
class FakeResponse:
    content: list[FakeBlock]
    stop_reason: str
    usage: FakeUsage
    model: str
    parsed_output: str = None


class FakeMessages:
    def __init__(self, response):
        self.response = response
        self.call_counts = 0

    def create(self, **kwargs):
        self.call_counts += 1
        return self.response

    def parse(self, **kwargs):
        self.call_counts += 1
        return self.response


class FakeClient:
    def __init__(self, response):
        self.messages = FakeMessages(response)


class FailingMessages:
    def create(self, **kwargs):
        request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")

        raise anthropic.APITimeoutError(request=request)


class FailingClient:
    def __init__(self):
        self.messages = FailingMessages()


class TruncatedMessages:
    def parse(self, **kwargs):
        return OrderDraft.model_validate_json('{"element_name": "zaw')
