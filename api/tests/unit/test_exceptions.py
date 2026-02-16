"""Unit tests for custom exceptions."""

from app.core.exceptions import (
    AppException,
    CacheUnavailableException,
    ModelNotLoadedException,
    MovieNotFoundException,
    UserNotFoundException,
)


class TestExceptions:
    """Tests for custom exception hierarchy."""

    def test_app_exception(self) -> None:
        exc = AppException(
            message="Something went wrong",
            error_code="GENERIC_ERROR",
            status_code=500,
        )
        assert exc.message == "Something went wrong"
        assert exc.error_code == "GENERIC_ERROR"
        assert exc.status_code == 500
        assert str(exc) == "Something went wrong"

    def test_user_not_found(self) -> None:
        exc = UserNotFoundException(user_id=42)
        assert exc.status_code == 404
        assert exc.error_code == "USER_NOT_FOUND"
        assert "42" in exc.message

    def test_movie_not_found(self) -> None:
        exc = MovieNotFoundException(movie_id=999)
        assert exc.status_code == 404
        assert exc.error_code == "MOVIE_NOT_FOUND"
        assert "999" in exc.message

    def test_model_not_loaded(self) -> None:
        exc = ModelNotLoadedException(model_name="als")
        assert exc.status_code == 503
        assert exc.error_code == "MODEL_NOT_LOADED"
        assert "als" in exc.message

    def test_cache_unavailable(self) -> None:
        exc = CacheUnavailableException()
        assert exc.status_code == 503
        assert exc.error_code == "CACHE_UNAVAILABLE"

    def test_exception_inheritance(self) -> None:
        exc = UserNotFoundException(user_id=1)
        assert isinstance(exc, AppException)
        assert isinstance(exc, Exception)
