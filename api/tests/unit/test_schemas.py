"""Unit tests for Pydantic schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.movie import MovieResponse, MovieSearchParams
from app.schemas.recommendation import RecommendationItem, RecommendationResponse
from app.schemas.user import RatingCreate


class TestMovieSchemas:
    """Tests for movie-related schemas."""

    def test_movie_response_valid(self) -> None:
        movie = MovieResponse(
            movie_id=1,
            title="Toy Story",
            genres=["Animation", "Comedy"],
            year=1995,
            avg_rating=3.89,
            rating_count=73215,
        )
        assert movie.movie_id == 1
        assert movie.title == "Toy Story"
        assert len(movie.genres) == 2

    def test_movie_response_nullable_fields(self) -> None:
        movie = MovieResponse(
            movie_id=1,
            title="Unknown Movie",
            avg_rating=0.0,
            rating_count=0,
        )
        assert movie.genres is None
        assert movie.year is None
        assert movie.imdb_id is None

    def test_search_params_defaults(self) -> None:
        params = MovieSearchParams()
        assert params.page == 1
        assert params.page_size == 20
        assert params.sort_by == "popularity"
        assert params.query is None

    def test_search_params_validation(self) -> None:
        params = MovieSearchParams(
            query="Matrix",
            genre="Sci-Fi",
            year_min=1990,
            year_max=2000,
            min_rating=4.0,
            page=2,
            page_size=50,
        )
        assert params.query == "Matrix"
        assert params.genre == "Sci-Fi"
        assert params.page == 2

    def test_search_params_invalid_page(self) -> None:
        with pytest.raises(ValidationError):
            MovieSearchParams(page=0)

    def test_search_params_invalid_page_size(self) -> None:
        with pytest.raises(ValidationError):
            MovieSearchParams(page_size=200)

    def test_search_params_invalid_min_rating(self) -> None:
        with pytest.raises(ValidationError):
            MovieSearchParams(min_rating=6.0)


class TestRecommendationSchemas:
    """Tests for recommendation-related schemas."""

    def test_recommendation_item_valid(self) -> None:
        item = RecommendationItem(
            movie_id=1,
            title="Toy Story",
            predicted_rating=4.5,
            explanation="Because you liked animated movies",
            confidence=0.85,
            model_source="als",
        )
        assert item.movie_id == 1
        assert item.model_source == "als"

    def test_recommendation_item_invalid_model_source(self) -> None:
        with pytest.raises(ValidationError):
            RecommendationItem(
                movie_id=1,
                title="Test",
                predicted_rating=4.0,
                explanation="test",
                confidence=0.5,
                model_source="invalid",
            )

    def test_recommendation_response_valid(self) -> None:
        response = RecommendationResponse(
            user_id=1,
            recommendations=[],
            strategy="collaborative",
            generated_at="2025-01-01T00:00:00Z",
            latency_ms=25.5,
        )
        assert response.user_id == 1
        assert response.cached is False


class TestUserSchemas:
    """Tests for user-related schemas."""

    def test_rating_create_valid(self) -> None:
        rating = RatingCreate(movie_id=1, rating=4.5)
        assert rating.movie_id == 1
        assert rating.rating == 4.5

    def test_rating_create_min_value(self) -> None:
        rating = RatingCreate(movie_id=1, rating=0.5)
        assert rating.rating == 0.5

    def test_rating_create_max_value(self) -> None:
        rating = RatingCreate(movie_id=1, rating=5.0)
        assert rating.rating == 5.0

    def test_rating_create_below_min(self) -> None:
        with pytest.raises(ValidationError):
            RatingCreate(movie_id=1, rating=0.0)

    def test_rating_create_above_max(self) -> None:
        with pytest.raises(ValidationError):
            RatingCreate(movie_id=1, rating=5.5)
