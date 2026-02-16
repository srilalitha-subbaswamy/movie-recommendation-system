import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Library } from 'lucide-react'
import SearchBar from '../components/SearchBar'
import GenreFilter from '../components/GenreFilter'
import MovieGrid from '../components/MovieGrid'
import LoadingSpinner from '../components/LoadingSpinner'
import { movieApi } from '../services/api'

function BrowsePage() {
  const [searchParams, setSearchParams] = useSearchParams()

  const [searchQuery, setSearchQuery] = useState(searchParams.get('query') || '')
  const [selectedGenre, setSelectedGenre] = useState<string | null>(
    searchParams.get('genre') || null
  )
  const [sortBy, setSortBy] = useState(searchParams.get('sort') || 'popularity')
  const [page, setPage] = useState(Number(searchParams.get('page')) || 1)

  // Sync URL params when filters change
  useEffect(() => {
    const params: Record<string, string> = {}
    if (searchQuery) params.query = searchQuery
    if (selectedGenre) params.genre = selectedGenre
    if (sortBy !== 'popularity') params.sort = sortBy
    if (page > 1) params.page = String(page)
    setSearchParams(params, { replace: true })
  }, [searchQuery, selectedGenre, sortBy, page, setSearchParams])

  const { data, isLoading, error } = useQuery({
    queryKey: ['movies', searchQuery, selectedGenre, sortBy, page],
    queryFn: () =>
      movieApi.search({
        query: searchQuery || undefined,
        genre: selectedGenre || undefined,
        sort_by: sortBy,
        page,
        page_size: 24,
      }),
    retry: 1,
  })

  const handleSearch = (query: string) => {
    setSearchQuery(query)
    setPage(1)
  }

  const handleGenreSelect = (genre: string | null) => {
    setSelectedGenre(genre)
    setPage(1)
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-2 mb-6">
        <Library className="w-6 h-6 text-primary-500" />
        <h1 className="text-2xl font-bold text-white">Browse Movies</h1>
        {data && (
          <span className="text-sm text-surface-500 ml-2">
            ({data.total} movies)
          </span>
        )}
      </div>

      {/* Search and Filters */}
      <div className="space-y-4 mb-8">
        <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center">
          <SearchBar onSearch={handleSearch} placeholder="Search movies..." initialValue={searchQuery} />

          <select
            value={sortBy}
            onChange={(e) => { setSortBy(e.target.value); setPage(1) }}
            className="input text-sm"
          >
            <option value="popularity">Most Popular</option>
            <option value="rating">Highest Rated</option>
            <option value="year">Newest First</option>
            <option value="title">A-Z</option>
          </select>
        </div>

        <GenreFilter selectedGenre={selectedGenre} onSelect={handleGenreSelect} />
      </div>

      {/* Results */}
      {isLoading && <LoadingSpinner text="Searching movies..." />}

      {error && (
        <div className="bg-surface-800 rounded-xl p-8 text-center">
          <p className="text-surface-400">
            Could not load movies. Make sure the API is running.
          </p>
        </div>
      )}

      {data && (
        <>
          <MovieGrid movies={data.movies} />

          {/* Pagination */}
          {data.total_pages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-8">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="btn-secondary text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <span className="text-sm text-surface-400">
                Page {page} of {data.total_pages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
                disabled={page === data.total_pages}
                className="btn-secondary text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default BrowsePage
