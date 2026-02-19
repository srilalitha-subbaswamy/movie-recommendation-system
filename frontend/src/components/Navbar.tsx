import { Link, useLocation } from 'react-router-dom'
import { Film, Home, Search, Sparkles, Star } from 'lucide-react'
import { useUser } from '../context/UserContext'

function Navbar() {
  const location = useLocation()
  const { currentUser, authUser } = useUser()

  const isActive = (path: string) =>
    location.pathname === path
      ? 'text-primary-500'
      : 'text-surface-400 hover:text-surface-100'

  // Generate initials for avatar
  const initials = currentUser.name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)

  return (
    <nav className="bg-surface-900 border-b border-surface-800 sticky top-0 z-50">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 group">
            <Film className="w-7 h-7 text-primary-500 group-hover:text-primary-400 transition-colors" />
            <span className="text-xl font-bold text-white">
              Movie<span className="text-primary-500">RecSys</span>
            </span>
          </Link>

          {/* Navigation */}
          <div className="flex items-center gap-1 sm:gap-4">
            <Link
              to="/"
              className={`flex items-center gap-1.5 text-sm font-medium transition-colors px-2 py-1 rounded-lg ${isActive('/')}`}
            >
              <Home className="w-4 h-4" />
              <span className="hidden sm:inline">Home</span>
            </Link>
            <Link
              to="/discover"
              className={`flex items-center gap-1.5 text-sm font-medium transition-colors px-2 py-1 rounded-lg ${isActive('/discover')}`}
            >
              <Sparkles className="w-4 h-4" />
              <span className="hidden sm:inline">Discover</span>
            </Link>
            <Link
              to="/browse"
              className={`flex items-center gap-1.5 text-sm font-medium transition-colors px-2 py-1 rounded-lg ${isActive('/browse')}`}
            >
              <Search className="w-4 h-4" />
              <span className="hidden sm:inline">Browse</span>
            </Link>
            <Link
              to="/my-ratings"
              className={`flex items-center gap-1.5 text-sm font-medium transition-colors px-2 py-1 rounded-lg ${isActive('/my-ratings')}`}
            >
              <Star className="w-4 h-4" />
              <span className="hidden sm:inline">My Ratings</span>
            </Link>
          </div>

          {/* Profile avatar */}
          <Link
            to="/profile"
            className="flex items-center gap-2 hover:opacity-80 transition-opacity"
          >
            {authUser?.avatar_url ? (
              <img
                src={authUser.avatar_url}
                alt={currentUser.name}
                className="w-8 h-8 rounded-full border-2 border-surface-700"
              />
            ) : (
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-600 to-violet-600 flex items-center justify-center border-2 border-surface-700">
                <span className="text-xs font-bold text-white">{initials}</span>
              </div>
            )}
            <span className="text-sm text-surface-300 hidden md:inline">
              {currentUser.name}
            </span>
          </Link>
        </div>
      </div>
    </nav>
  )
}

export default Navbar
