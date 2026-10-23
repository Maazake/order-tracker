from typing import Annotated

import anthropic
from fastapi import Depends, HTTPException, status

from app.config import settings

_client = None


def get_llm_client() -> anthropic.Anthropic:
    global _client

    if settings.anthropic_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="There is not Anthropic API Key",
        )

    if _client is None:
        api_key = settings.anthropic_api_key.get_secret_value()
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


LlmClient = Annotated[anthropic.Anthropic, Depends(get_llm_client)]
