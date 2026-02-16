const GENRES = [
  'Action', 'Adventure', 'Animation', 'Children', 'Comedy',
  'Crime', 'Drama', 'Fantasy', 'Horror', 'Mystery',
  'Romance', 'Sci-Fi', 'Thriller', 'War', 'Western',
]

interface GenreFilterProps {
  selectedGenre: string | null
  onSelect: (genre: string | null) => void
}

function GenreFilter({ selectedGenre, onSelect }: GenreFilterProps) {
  return (
    <div className="flex flex-wrap gap-2">
      <button
        onClick={() => onSelect(null)}
        className={`text-xs font-medium px-3 py-1.5 rounded-full transition-colors ${
          selectedGenre === null
            ? 'bg-primary-600 text-white'
            : 'bg-surface-800 text-surface-400 hover:bg-surface-700 hover:text-surface-200'
        }`}
      >
        All
      </button>
      {GENRES.map((genre) => (
        <button
          key={genre}
          onClick={() => onSelect(genre === selectedGenre ? null : genre)}
          className={`text-xs font-medium px-3 py-1.5 rounded-full transition-colors ${
            selectedGenre === genre
              ? 'bg-primary-600 text-white'
              : 'bg-surface-800 text-surface-400 hover:bg-surface-700 hover:text-surface-200'
          }`}
        >
          {genre}
        </button>
      ))}
    </div>
  )
}

export default GenreFilter
