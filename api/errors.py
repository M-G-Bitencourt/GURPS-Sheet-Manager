"""Domain level errors translated into JSON HTTP responses."""


class ApiError(Exception):
    """Base error carrying an HTTP status code and a user-facing message."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class NotFoundError(ApiError):
    """Raised when a requested record or resource does not exist."""

    def __init__(self, message: str = "Registro não encontrado.") -> None:
        super().__init__(message, 404)


class ConflictError(ApiError):
    """Raised when a write operation violates a database constraint."""

    def __init__(self, message: str) -> None:
        super().__init__(message, 409)
