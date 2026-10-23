from typing import Annotated

import anthropic
from fastapi import Depends

client = anthropic.Anthropic()


def get_llm_client():
    client = anthropic.Anthropic()
    try:
        yield client
    finally:
        pass


LlmClient = Annotated[anthropic.Anthropic, Depends(get_llm_client)]
