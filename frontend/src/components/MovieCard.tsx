import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Film, Star, TrendingUp } from 'lucide-react'
import type { Movie } from '../services/api'

interface MovieCardProps {
  movie: Movie
  explanation?: string
}

const GENRE_COLORS: Record<string, string> = {
  Action: 'bg-red-900/50 text-red-300',
  Comedy: 'bg-yellow-900/50 text-yellow-300',
  Drama: 'bg-blue-900/50 text-blue-300',
  'Sci-Fi': 'bg-purple-900/50 text-purple-300',
  Thriller: 'bg-orange-900/50 text-orange-300',
  Animation: 'bg-green-900/50 text-green-300',
  Romance: 'bg-pink-900/50 text-pink-300',
  Horror: 'bg-gray-900/50 text-gray-300',
  Adventure: 'bg-emerald-900/50 text-emerald-300',
  Fantasy: 'bg-indigo-900/50 text-indigo-300',
  Crime: 'bg-amber-900/50 text-amber-300',
  War: 'bg-stone-900/50 text-stone-300',
}

function MovieCard({ movie, explanation }: MovieCardProps) {
  const [imgError, setImgError] = useState(false)
  const hasPoster = movie.poster_url && !imgError

  const getGenreColor = (genre: string) =>
    GENRE_COLORS[genre] || 'bg-surface-700 text-surface-300'

  return (
    <Link to={`/movie/${movie.movie_id}`} className="card group cursor-pointer">
      {/* Poster */}
      <div className="aspect-[2/3] bg-gradient-to-br from-surface-700 to-surface-800 relative overflow-hidden">
        {hasPoster ? (
          <img
            src={movie.poster_url!}
            alt={movie.title}
            loading="lazy"
            onError={() => setImgError(true)}
            className="absolute inset-0 w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center">
            <Film className="w-12 h-12 text-surface-600 group-hover:text-surface-500 transition-colors" />
          </div>
        )}

        {/* Rating badge */}
        <div className="absolute top-2 right-2 bg-black/70 backdrop-blur-sm rounded-lg px-2 py-1 flex items-center gap-1">
          <Star className="w-3.5 h-3.5 text-yellow-400 fill-yellow-400" />
          <span className="text-sm font-semibold text-white">
            {movie.avg_rating.toFixed(1)}
          </span>
        </div>

        {/* Year badge */}
        {movie.year && (
          <div className="absolute top-2 left-2 bg-black/70 backdrop-blur-sm rounded-lg px-2 py-1">
            <span className="text-xs font-medium text-surface-300">{movie.year}</span>
          </div>
        )}
      </div>

      {/* Info */}
      <div className="p-3">
        <h3 className="font-semibold text-white text-sm leading-tight line-clamp-2 mb-2 group-hover:text-primary-400 transition-colors">
          {movie.title}
        </h3>

        {/* Genres */}
        <div className="flex flex-wrap gap-1 mb-2">
          {movie.genres?.slice(0, 3).map((genre) => (
            <span
              key={genre}
              className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${getGenreColor(genre)}`}
            >
              {genre}
            </span>
          ))}
        </div>

        {/* Rating count */}
        {movie.rating_count > 0 && (
          <div className="flex items-center gap-1 text-xs text-surface-400">
            <TrendingUp className="w-3 h-3" />
            <span>{movie.rating_count} ratings</span>
          </div>
        )}

        {/* Explanation */}
        {explanation && (
          <p className="mt-2 text-xs text-primary-400 italic line-clamp-2">{explanation}</p>
        )}
      </div>
    </Link>
  )
}

export default MovieCard
