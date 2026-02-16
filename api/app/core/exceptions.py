"""Custom application exceptions with structured error codes."""


class AppException(Exception):
    """Base exception for application errors."""

    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 400,
    ) -> None:
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(message)


class UserNotFoundException(AppException):
    """Raised when a user is not found."""

    def __init__(self, user_id: int) -> None:
        super().__init__(
            message=f"User {user_id} not found",
            error_code="USER_NOT_FOUND",
            status_code=404,
        )


class MovieNotFoundException(AppException):
    """Raised when a movie is not found."""

    def __init__(self, movie_id: int) -> None:
        super().__init__(
            message=f"Movie {movie_id} not found",
            error_code="MOVIE_NOT_FOUND",
            status_code=404,
        )


class ModelNotLoadedException(AppException):
    """Raised when a model is not available for inference."""

    def __init__(self, model_name: str) -> None:
        super().__init__(
            message=f"Model '{model_name}' is not loaded or unavailable",
            error_code="MODEL_NOT_LOADED",
            status_code=503,
        )


class CacheUnavailableException(AppException):
    """Raised when Redis cache is unavailable."""

    def __init__(self) -> None:
        super().__init__(
            message="Cache service is temporarily unavailable",
            error_code="CACHE_UNAVAILABLE",
            status_code=503,
        )
