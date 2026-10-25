from dataclasses import dataclass


@dataclass
class FakeBlock:
    type: str
    text: str


@dataclass
class FakeResponse:
    content: list[FakeBlock]
    stop_reason: str


class FakeMessages:
    def __init__(self, response):
        self.response = response
        self.call_counts = 0

    def create(self, **kwargs):
        self.call_counts += 1
        return self.response


class FakeClient:
    def __init__(self, response):
        self.messages = FakeMessages(response)
