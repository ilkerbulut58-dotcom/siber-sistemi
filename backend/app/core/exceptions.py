"""Application-level exceptions mapped to API error responses."""


class AppError(Exception):
    """Raised for expected business-rule failures."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        details: list | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or []
        super().__init__(message)
