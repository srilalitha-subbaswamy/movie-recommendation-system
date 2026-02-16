import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Star, TrendingUp, Clock, ExternalLink, Check } from 'lucide-react'
import { useUser } from '../context/UserContext'
import RatingStars from '../components/RatingStars'
import RecommendationCarousel from '../components/RecommendationCarousel'
import LoadingSpinner from '../components/LoadingSpinner'
import { movieApi, recommendationApi, userApi } from '../services/api'

function MovieDetailPage() {
  const { movieId } = useParams<{ movieId: string }>()
  const id = Number(movieId)
  const { currentUser } = useUser()
  const queryClient = useQueryClient()

  const { data: movie, isLoading, error } = useQuery({
    queryKey: ['movie', id],
    queryFn: () => movieApi.getById(id),
    enabled: !isNaN(id),
  })

  const { data: similar, isLoading: similarLoading } = useQuery({
    queryKey: ['similar', id],
    queryFn: () => recommendationApi.getSimilar(id),
    enabled: !isNaN(id),
  })

  // Fetch user's existing rating for this movie (survives page refresh)
  const { data: existingRating } = useQuery({
    queryKey: ['my-rating', currentUser.id, id],
    queryFn: () => userApi.getRatingForMovie(currentUser.id, id),
    enabled: !isNaN(id),
  })

  const rateMutation = useMutation({
    mutationFn: (rating: number) =>
      userApi.rateMovie(currentUser.id, id, rating),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-rating', currentUser.id, id] })
      queryClient.invalidateQueries({ queryKey: ['recommendations'] })
      queryClient.invalidateQueries({ queryKey: ['user-ratings'] })
      queryClient.invalidateQueries({ queryKey: ['rating-stats'] })
    },
  })

  const handleRate = (rating: number) => {
    rateMutation.mutate(rating)
  }

  const userRating = existingRating?.rating ?? null

  if (isLoading) {
    return <LoadingSpinner text="Loading movie details..." size="lg" />
  }

  if (error || !movie) {
    return (
      <div className="text-center py-20">
        <p className="text-surface-400 text-lg">Movie not found</p>
        <Link to="/browse" className="btn-primary mt-4 inline-block">
          Browse Movies
        </Link>
      </div>
    )
  }

  return (
    <div>
      {/* Back button */}
      <Link
        to="/browse"
        className="inline-flex items-center gap-1.5 text-sm text-surface-400 hover:text-white transition-colors mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Browse
      </Link>

      {/* Movie header */}
      <div className="flex flex-col md:flex-row gap-8 mb-12">
        {/* Poster */}
        <div className="flex-shrink-0 w-full md:w-64">
          <div className="aspect-[2/3] bg-gradient-to-br from-surface-700 to-surface-800 rounded-xl overflow-hidden">
            {movie.poster_url ? (
              <img
                src={movie.poster_url}
                alt={movie.title}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <svg
                  className="w-20 h-20 text-surface-600"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <rect width="18" height="18" x="3" y="3" rx="2" ry="2" />
                  <line x1="7" x2="7" y1="3" y2="21" />
                  <line x1="17" x2="17" y1="3" y2="21" />
                </svg>
              </div>
            )}
          </div>
        </div>

        {/* Movie info */}
        <div className="flex-1">
          <h1 className="text-3xl font-bold text-white mb-2">{movie.title}</h1>

          <div className="flex items-center gap-4 mb-4">
            {movie.year && (
              <span className="flex items-center gap-1 text-surface-400">
                <Clock className="w-4 h-4" />
                {movie.year}
              </span>
            )}
            <div className="flex items-center gap-1">
              <Star className="w-4 h-4 text-yellow-400 fill-yellow-400" />
              <span className="font-semibold text-white">{movie.avg_rating.toFixed(1)}</span>
              <span className="text-surface-400">/5</span>
            </div>
            {movie.rating_count > 0 && (
              <span className="flex items-center gap-1 text-surface-400">
                <TrendingUp className="w-4 h-4" />
                {movie.rating_count >= 1000
                  ? `${(movie.rating_count / 1000).toFixed(1)}K ratings`
                  : `${movie.rating_count} ratings`}
              </span>
            )}
          </div>

          {/* Community rating display */}
          <RatingStars rating={movie.avg_rating} size="lg" />

          {/* User rating section */}
          <div className="mt-6 p-4 bg-surface-800/50 rounded-xl border border-surface-700">
            <p className="text-sm font-medium text-surface-300 mb-2">
              {userRating !== null ? 'Your rating' : 'Rate this movie'}
            </p>
            <div className="flex items-center gap-3">
              <RatingStars
                rating={userRating ?? 0}
                size="lg"
                showValue={false}
                interactive={!rateMutation.isPending}
                onRate={handleRate}
              />
              {rateMutation.isPending && (
                <span className="text-xs text-surface-400 animate-pulse">Saving...</span>
              )}
              {userRating !== null && !rateMutation.isPending && (
                <span className="flex items-center gap-1 text-xs text-green-400">
                  <Check className="w-3.5 h-3.5" />
                  Rated {userRating}/5
                </span>
              )}
              {rateMutation.isError && (
                <span className="text-xs text-red-400">Failed to save rating</span>
              )}
            </div>
          </div>

          {/* Genres */}
          <div className="flex flex-wrap gap-2 mt-6">
            {movie.genres?.map((genre) => (
              <Link
                key={genre}
                to={`/browse?genre=${genre}`}
                className="text-sm font-medium bg-surface-800 text-surface-300 px-3 py-1.5 rounded-full hover:bg-surface-700 transition-colors"
              >
                {genre}
              </Link>
            ))}
          </div>

          {/* External links */}
          <div className="flex gap-3 mt-6">
            {movie.imdb_id && (
              <a
                href={`https://www.imdb.com/title/tt${movie.imdb_id}/`}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-secondary text-sm flex items-center gap-1.5"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                IMDb
              </a>
            )}
            {movie.tmdb_id && (
              <a
                href={`https://www.themoviedb.org/movie/${movie.tmdb_id}`}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-secondary text-sm flex items-center gap-1.5"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                TMDb
              </a>
            )}
          </div>
        </div>
      </div>

      {/* Similar movies */}
      {similarLoading && <LoadingSpinner text="Finding similar movies..." />}

      {similar && similar.similar_movies.length > 0 && (
        <RecommendationCarousel
          title="Similar Movies"
          subtitle={`Movies like ${movie.title}`}
          items={similar.similar_movies}
          latencyMs={similar.latency_ms}
        />
      )}
    </div>
  )
}

export default MovieDetailPage
