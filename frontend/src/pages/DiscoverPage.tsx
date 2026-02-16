import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Sparkles, Search, Clock } from 'lucide-react'
import MovieGrid from '../components/MovieGrid'
import LoadingSpinner from '../components/LoadingSpinner'
import { discoverApi } from '../services/api'
import type { Movie } from '../services/api'

const EXAMPLE_QUERIES = [
  'light hearted comedies',
  'dark psychological thriller',
  'feel-good family films',
  'mind-bending sci-fi',
  'classic detective noir',
  'romantic drama',
  'epic adventure fantasy',
  'quirky indie comedy',
  'suspenseful crime mystery',
  'animated movies for all ages',
]

function DiscoverPage() {
  const [query, setQuery] = useState('')
  const [submittedQuery, setSubmittedQuery] = useState('')

  const { data, isLoading, error } = useQuery({
    queryKey: ['discover', submittedQuery],
    queryFn: () => discoverApi.search(submittedQuery, 30),
    enabled: submittedQuery.length >= 2,
    retry: 1,
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim().length >= 2) {
      setSubmittedQuery(query.trim())
    }
  }

  const handleChipClick = (example: string) => {
    setQuery(example)
    setSubmittedQuery(example)
  }

  // Convert discover items to Movie objects for MovieGrid
  const movies: Movie[] =
    data?.items.map((item) => ({
      movie_id: item.movie_id,
      title: item.title,
      genres: item.genres,
      year: item.year,
      poster_url: item.poster_url,
      avg_rating: item.avg_rating,
      rating_count: item.rating_count,
    })) ?? []

  return (
    <div>
      {/* Hero */}
      <section className="mb-10">
        <div className="relative bg-gradient-to-br from-violet-950 via-surface-900 to-surface-950 rounded-2xl p-8 md:p-12 overflow-hidden">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_50%,rgba(139,92,246,0.15),transparent_50%)]" />
          <div className="relative z-10">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles className="w-5 h-5 text-violet-400" />
              <span className="text-sm font-medium text-violet-400">Semantic Search</span>
            </div>
            <h1 className="text-3xl md:text-4xl font-bold text-white mb-3">
              Discover Movies by
              <span className="text-violet-400"> Description</span>
            </h1>
            <p className="text-surface-400 max-w-xl text-lg mb-8">
              Describe the kind of movie you're in the mood for and we'll find the best matches
              using AI-powered semantic search.
            </p>

            {/* Search input */}
            <form onSubmit={handleSubmit} className="relative max-w-2xl">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-surface-400" />
              <input
                type="text"
                value={query}
                onChange={(e) => {
                  const newVal = e.target.value
                  setQuery(newVal)
                  if (newVal.trim() === '') {
                    setSubmittedQuery('')
                  }
                }}
                placeholder="Describe the kind of movie you want..."
                className="w-full pl-12 pr-28 py-4 bg-surface-800/80 border border-surface-700 rounded-xl text-white placeholder-surface-500 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent text-lg"
              />
              <button
                type="submit"
                disabled={query.trim().length < 2}
                className="absolute right-2 top-1/2 -translate-y-1/2 bg-violet-600 hover:bg-violet-500 disabled:bg-surface-700 disabled:text-surface-500 text-white px-5 py-2.5 rounded-lg font-medium transition-colors"
              >
                Discover
              </button>
            </form>

            {/* Example chips */}
            <div className="flex flex-wrap gap-2 mt-5">
              {EXAMPLE_QUERIES.map((example) => (
                <button
                  key={example}
                  onClick={() => handleChipClick(example)}
                  className="text-xs font-medium bg-surface-800/60 text-surface-300 px-3 py-1.5 rounded-full border border-surface-700 hover:border-violet-500/50 hover:text-violet-300 transition-colors cursor-pointer"
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Results */}
      {isLoading && <LoadingSpinner text="Searching with AI..." />}

      {error && (
        <div className="bg-surface-800 rounded-xl p-8 text-center">
          <p className="text-surface-400">
            Could not perform search. Make sure the API is running.
          </p>
        </div>
      )}

      {data && submittedQuery && (
        <section>
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-xl font-bold text-white">
                Results for "{data.query}"
              </h2>
              <p className="text-sm text-surface-400 mt-1">
                {data.total} movies found
              </p>
            </div>
            <div className="flex items-center gap-2 text-xs text-surface-500">
              <Clock className="w-3.5 h-3.5" />
              {data.latency_ms.toFixed(0)}ms
            </div>
          </div>

          {/* Tags preview for top results */}
          {data.items.length > 0 && data.items[0].matched_tags.length > 0 && (
            <div className="mb-6 p-4 bg-surface-800/50 rounded-xl border border-surface-700/50">
              <p className="text-xs font-medium text-surface-400 mb-2">
                Matching tags from the community:
              </p>
              <div className="flex flex-wrap gap-1.5">
                {[...new Set(data.items.slice(0, 5).flatMap((i) => i.matched_tags))].slice(0, 20).map((tag) => (
                  <span
                    key={tag}
                    className="text-xs bg-violet-900/30 text-violet-300 px-2 py-0.5 rounded-full"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          <MovieGrid movies={movies} />
        </section>
      )}

      {/* Empty state */}
      {!submittedQuery && !isLoading && (
        <div className="text-center py-16">
          <Sparkles className="w-12 h-12 text-surface-700 mx-auto mb-4" />
          <p className="text-surface-500 text-lg">
            Try describing the kind of movie you're looking for
          </p>
          <p className="text-surface-600 text-sm mt-1">
            Click an example chip above or type your own description
          </p>
        </div>
      )}
    </div>
  )
}

export default DiscoverPage
