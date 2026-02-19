import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Star, Film, ArrowRight, BarChart3 } from 'lucide-react'
import { useUser } from '../context/UserContext'
import LoadingSpinner from '../components/LoadingSpinner'
import { userApi } from '../services/api'

function ProfilePage() {
  const { currentUser, users, setCurrentUser, authUser, logout } = useUser()

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['rating-stats', currentUser.id],
    queryFn: () => userApi.getRatingStats(currentUser.id),
  })

  const topGenres = stats?.genre_breakdown
    ? Object.entries(stats.genre_breakdown).slice(0, 5)
    : []

  // Generate initials and a color for the avatar
  const initials = currentUser.name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)

  const avatarColors = [
    'from-primary-600 to-primary-800',
    'from-violet-600 to-violet-800',
    'from-emerald-600 to-emerald-800',
    'from-amber-600 to-amber-800',
    'from-cyan-600 to-cyan-800',
    'from-pink-600 to-pink-800',
    'from-blue-600 to-blue-800',
  ]
  const colorIdx = currentUser.id % avatarColors.length
  const avatarColor = avatarColors[colorIdx]

  return (
    <div className="max-w-2xl mx-auto">
      {/* Profile Card */}
      <div className="bg-surface-800 rounded-2xl border border-surface-700 overflow-hidden mb-8">
        {/* Banner */}
        <div className="h-24 bg-gradient-to-r from-primary-900 via-surface-800 to-violet-900" />

        {/* Avatar & Info */}
        <div className="px-6 pb-6 -mt-10">
          <div className="flex items-end gap-4 mb-6">
            {authUser?.avatar_url ? (
              <img
                src={authUser.avatar_url}
                alt={currentUser.name}
                className="w-20 h-20 rounded-full border-4 border-surface-800 object-cover"
              />
            ) : (
              <div
                className={`w-20 h-20 rounded-full border-4 border-surface-800 bg-gradient-to-br ${avatarColor} flex items-center justify-center`}
              >
                <span className="text-2xl font-bold text-white">{initials}</span>
              </div>
            )}
            <div className="mb-1">
              <h1 className="text-2xl font-bold text-white">{currentUser.name}</h1>
              {authUser?.email && (
                <p className="text-sm text-surface-400">{authUser.email}</p>
              )}
              {!authUser && (
                <p className="text-sm text-surface-500">Demo User #{currentUser.id}</p>
              )}
            </div>
          </div>

          {/* Stats */}
          {statsLoading && <LoadingSpinner text="Loading stats..." />}
          {stats && (
            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="text-center p-3 bg-surface-700/50 rounded-xl">
                <p className="text-2xl font-bold text-white">{stats.total_rated}</p>
                <p className="text-xs text-surface-400">Movies Rated</p>
              </div>
              <div className="text-center p-3 bg-surface-700/50 rounded-xl">
                <div className="flex items-center justify-center gap-1">
                  <p className="text-2xl font-bold text-white">{stats.avg_rating}</p>
                  <Star className="w-4 h-4 text-yellow-400 fill-yellow-400" />
                </div>
                <p className="text-xs text-surface-400">Avg Rating</p>
              </div>
              <div className="text-center p-3 bg-surface-700/50 rounded-xl">
                <p className="text-2xl font-bold text-white">
                  {topGenres.length > 0 ? topGenres[0][0] : '—'}
                </p>
                <p className="text-xs text-surface-400">Top Genre</p>
              </div>
            </div>
          )}

          {/* Top Genres */}
          {topGenres.length > 0 && (
            <div className="mb-6">
              <h3 className="text-sm font-medium text-surface-400 mb-2">Favorite Genres</h3>
              <div className="flex flex-wrap gap-2">
                {topGenres.map(([genre, count]) => (
                  <span
                    key={genre}
                    className="text-xs font-medium bg-surface-700 text-surface-300 px-3 py-1.5 rounded-full"
                  >
                    {genre} ({count})
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Quick Links */}
          <div className="space-y-2">
            <Link
              to="/my-ratings"
              className="flex items-center justify-between p-3 bg-surface-700/50 rounded-xl hover:bg-surface-700 transition-colors group"
            >
              <div className="flex items-center gap-3">
                <Star className="w-5 h-5 text-yellow-400" />
                <span className="text-sm font-medium text-white">View My Ratings</span>
              </div>
              <ArrowRight className="w-4 h-4 text-surface-500 group-hover:text-white transition-colors" />
            </Link>

            <Link
              to="/discover"
              className="flex items-center justify-between p-3 bg-surface-700/50 rounded-xl hover:bg-surface-700 transition-colors group"
            >
              <div className="flex items-center gap-3">
                <Film className="w-5 h-5 text-violet-400" />
                <span className="text-sm font-medium text-white">Discover Movies</span>
              </div>
              <ArrowRight className="w-4 h-4 text-surface-500 group-hover:text-white transition-colors" />
            </Link>

            <Link
              to="/browse"
              className="flex items-center justify-between p-3 bg-surface-700/50 rounded-xl hover:bg-surface-700 transition-colors group"
            >
              <div className="flex items-center gap-3">
                <BarChart3 className="w-5 h-5 text-emerald-400" />
                <span className="text-sm font-medium text-white">Browse All Movies</span>
              </div>
              <ArrowRight className="w-4 h-4 text-surface-500 group-hover:text-white transition-colors" />
            </Link>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="bg-surface-800 rounded-2xl border border-surface-700 p-6">
        <h2 className="text-sm font-semibold text-surface-400 mb-4 uppercase tracking-wider">
          Account
        </h2>

        {authUser ? (
          <button
            onClick={logout}
            className="w-full py-2.5 px-4 bg-red-900/30 text-red-400 rounded-xl hover:bg-red-900/50 transition-colors text-sm font-medium"
          >
            Sign Out
          </button>
        ) : (
          <div>
            <p className="text-xs text-surface-500 mb-3">
              You're using a demo account. Switch between demo users below:
            </p>
            <select
              value={currentUser.id}
              onChange={(e) => setCurrentUser(Number(e.target.value))}
              className="w-full bg-surface-700 border border-surface-600 rounded-xl px-4 py-2.5 text-sm text-surface-300 focus:outline-none focus:ring-2 focus:ring-primary-500 cursor-pointer"
            >
              {users.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.name} ({user.ratingCount} ratings)
                </option>
              ))}
            </select>
          </div>
        )}
      </div>
    </div>
  )
}

export default ProfilePage
