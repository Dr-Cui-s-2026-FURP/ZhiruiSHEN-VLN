class APIHandler:
    """Reserved API mode handler for future extension.

    This project currently runs local-only inference. API mode is intentionally
    disabled but this placeholder keeps extension points explicit.
    """

    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled

    def is_enabled(self) -> bool:
        return self.enabled
