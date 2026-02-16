import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Star, Trash2, Film, BarChart3 } from 'lucide-react'
import { useUser } from '../context/UserContext'
import RatingStars from '../components/RatingStars'
import LoadingSpinner from '../components/LoadingSpinner'
import { userApi } from '../services/api'

function MyRatingsPage() {
  const { currentUser } = useUser()
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [sortBy] = useState('date_desc')
  const pageSize = 20

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['rating-stats', currentUser.id],
    queryFn: () => userApi.getRatingStats(currentUser.id),
  })

  const { data: ratingsData, isLoading: ratingsLoading } = useQuery({
    queryKey: ['user-ratings', currentUser.id, page, sortBy],
    queryFn: () => userApi.getRatings(currentUser.id, page, pageSize, sortBy),
  })

  const deleteMutation = useMutation({
    mutationFn: (movieId: number) => userApi.deleteRating(currentUser.id, movieId),
    onSuccess: (_data, movieId) => {
      queryClient.invalidateQueries({ queryKey: ['user-ratings'] })
      queryClient.invalidateQueries({ queryKey: ['rating-stats'] })
      queryClient.invalidateQueries({ queryKey: ['recommendations'] })
      queryClient.invalidateQueries({ queryKey: ['my-rating', currentUser.id, movieId] })
    },
  })

  const rateMutation = useMutation({
    mutationFn: ({ movieId, rating }: { movieId: number; rating: number }) =>
      userApi.rateMovie(currentUser.id, movieId, rating),
    onSuccess: (_data, { movieId }) => {
      queryClient.invalidateQueries({ queryKey: ['user-ratings'] })
      queryClient.invalidateQueries({ queryKey: ['rating-stats'] })
      queryClient.invalidateQueries({ queryKey: ['my-rating', currentUser.id, movieId] })
    },
  })

  const totalPages = ratingsData ? Math.ceil(ratingsData.total / pageSize) : 0

  const topGenre = stats?.genre_breakdown
    ? Object.entries(stats.genre_breakdown)[0]
    : null

  const genreEntries = stats?.genre_breakdown
    ? Object.entries(stats.genre_breakdown).slice(0, 10)
    : []
  const maxGenreCount = genreEntries.length > 0 ? genreEntries[0][1] : 1

  const ratingBuckets = ['1.0', '1.5', '2.0', '2.5', '3.0', '3.5', '4.0', '4.5', '5.0']
  const maxDistCount = stats?.rating_distribution
    ? Math.max(...Object.values(stats.rating_distribution), 1)
    : 1

  return (
    <div>
      <div className="flex items-center gap-2 mb-8">
        <Star className="w-6 h-6 text-yellow-400 fill-yellow-400" />
        <h1 className="text-2xl font-bold text-white">My Ratings</h1>
        <span className="text-sm text-surface-500 ml-2">
          as {currentUser.name}
        </span>
      </div>

      {/* Stats Summary */}
      {statsLoading && <LoadingSpinner text="Loading stats..." />}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <div className="bg-surface-800 rounded-xl p-5 border border-surface-700">
            <p className="text-sm text-surface-400 mb-1">Movies Rated</p>
            <p className="text-3xl font-bold text-white">{stats.total_rated}</p>
          </div>
          <div className="bg-surface-800 rounded-xl p-5 border border-surface-700">
            <p className="text-sm text-surface-400 mb-1">Average Rating</p>
            <div className="flex items-center gap-2">
              <p className="text-3xl font-bold text-white">{stats.avg_rating}</p>
              <Star className="w-6 h-6 text-yellow-400 fill-yellow-400" />
            </div>
          </div>
          <div className="bg-surface-800 rounded-xl p-5 border border-surface-700">
            <p className="text-sm text-surface-400 mb-1">Top Genre</p>
            <p className="text-3xl font-bold text-white">
              {topGenre ? topGenre[0] : '—'}
            </p>
            {topGenre && (
              <p className="text-xs text-surface-500">{topGenre[1]} movies</p>
            )}
          </div>
        </div>
      )}

      {/* Genre Breakdown & Rating Distribution */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div className="bg-surface-800 rounded-xl p-5 border border-surface-700">
            <div className="flex items-center gap-2 mb-4">
              <BarChart3 className="w-4 h-4 text-surface-400" />
              <h3 className="text-sm font-semibold text-surface-300">Genre Breakdown</h3>
            </div>
            <div className="space-y-2">
              {genreEntries.map(([genre, count]) => (
                <div key={genre} className="flex items-center gap-3">
                  <span className="text-xs text-surface-400 w-20 truncate">{genre}</span>
                  <div className="flex-1 h-5 bg-surface-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary-600 rounded-full transition-all"
                      style={{ width: `${(count / maxGenreCount) * 100}%` }}
                    />
                  </div>
                  <span className="text-xs text-surface-500 w-8 text-right">{count}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-surface-800 rounded-xl p-5 border border-surface-700">
            <div className="flex items-center gap-2 mb-4">
              <Star className="w-4 h-4 text-surface-400" />
              <h3 className="text-sm font-semibold text-surface-300">Rating Distribution</h3>
            </div>
            <div className="space-y-2">
              {ratingBuckets.map((bucket) => {
                const count = stats.rating_distribution[bucket] || 0
                return (
                  <div key={bucket} className="flex items-center gap-3">
                    <span className="text-xs text-surface-400 w-8">{bucket}</span>
                    <Star className="w-3 h-3 text-yellow-400 fill-yellow-400" />
                    <div className="flex-1 h-5 bg-surface-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-yellow-600 rounded-full transition-all"
                        style={{ width: `${(count / maxDistCount) * 100}%` }}
                      />
                    </div>
                    <span className="text-xs text-surface-500 w-8 text-right">{count}</span>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}

      {/* Rating List */}
      {ratingsLoading && <LoadingSpinner text="Loading ratings..." />}
      {ratingsData && (
        <>
          <div className="space-y-3">
            {ratingsData.ratings.map((r) => (
              <div
                key={`${r.user_id}-${r.movie_id}`}
                className="flex items-center gap-4 bg-surface-800 rounded-xl p-4 border border-surface-700 hover:border-surface-600 transition-colors"
              >
                {/* Movie poster */}
                <Link
                  to={`/movie/${r.movie_id}`}
                  className="flex-shrink-0 w-12 h-16 bg-surface-700 rounded-lg overflow-hidden hover:opacity-80 transition-opacity"
                >
                  {r.movie_poster_url ? (
                    <img
                      src={r.movie_poster_url}
                      alt={r.movie_title}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <Film className="w-5 h-5 text-surface-500" />
                    </div>
                  )}
                </Link>

                {/* Movie info */}
                <div className="flex-1 min-w-0">
                  <Link
                    to={`/movie/${r.movie_id}`}
                    className="font-medium text-white hover:text-primary-400 transition-colors text-sm line-clamp-1"
                  >
                    {r.movie_title}
                  </Link>
                  <div className="flex items-center gap-2 mt-0.5">
                    {r.movie_year && (
                      <span className="text-xs text-surface-500">{r.movie_year}</span>
                    )}
                    {r.movie_genres && r.movie_genres.length > 0 && (
                      <span className="text-xs text-surface-500">
                        {r.movie_genres.slice(0, 2).join(', ')}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-surface-600 mt-0.5">
                    Rated on {new Date(r.timestamp).toLocaleDateString()}
                  </p>
                </div>

                {/* Rating stars (interactive for re-rating) */}
                <div className="flex-shrink-0">
                  <RatingStars
                    rating={r.rating}
                    size="sm"
                    interactive
                    onRate={(newRating) =>
                      rateMutation.mutate({ movieId: r.movie_id, rating: newRating })
                    }
                  />
                </div>

                {/* Delete button */}
                <button
                  onClick={() => {
                    if (window.confirm('Remove this rating?')) {
                      deleteMutation.mutate(r.movie_id)
                    }
                  }}
                  className="flex-shrink-0 p-2 text-surface-500 hover:text-red-400 transition-colors rounded-lg hover:bg-surface-700"
                  title="Delete rating"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-8">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="btn-secondary text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <span className="text-sm text-surface-400">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="btn-secondary text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}

      {ratingsData && ratingsData.ratings.length === 0 && (
        <div className="text-center py-16">
          <Star className="w-12 h-12 text-surface-700 mx-auto mb-4" />
          <p className="text-surface-500 text-lg">No ratings yet</p>
          <Link to="/browse" className="btn-primary mt-4 inline-block">
            Browse Movies to Rate
          </Link>
        </div>
      )}
    </div>
  )
}

export default MyRatingsPage
