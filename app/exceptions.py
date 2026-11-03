class NotFoundError(Exception):
    pass


class ConflictError(Exception):
    pass


class LlmUnavailableError(Exception):
    pass


class LlmLimitExceededError(Exception):
    pass
