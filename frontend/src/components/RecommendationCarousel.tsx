import { useRef } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import type { RecommendationItem } from '../services/api'
import MovieCard from './MovieCard'

interface RecommendationCarouselProps {
  title: string
  subtitle?: string
  items: RecommendationItem[]
  strategy?: string
  latencyMs?: number
}

function RecommendationCarousel({
  title,
  subtitle,
  items,
  strategy,
  latencyMs,
}: RecommendationCarouselProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

  const scroll = (direction: 'left' | 'right') => {
    if (scrollRef.current) {
      const scrollAmount = 300
      scrollRef.current.scrollBy({
        left: direction === 'left' ? -scrollAmount : scrollAmount,
        behavior: 'smooth',
      })
    }
  }

  return (
    <section className="mb-10">
      {/* Header */}
      <div className="flex items-end justify-between mb-4">
        <div>
          <h2 className="text-xl font-bold text-white">{title}</h2>
          {subtitle && (
            <p className="text-sm text-surface-400 mt-0.5">{subtitle}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {strategy && (
            <span className="text-xs bg-primary-900/50 text-primary-300 px-2 py-1 rounded-full">
              {strategy}
            </span>
          )}
          {latencyMs !== undefined && (
            <span className="text-xs text-surface-500">{latencyMs.toFixed(0)}ms</span>
          )}
          <button
            onClick={() => scroll('left')}
            className="p-1.5 rounded-lg bg-surface-800 hover:bg-surface-700 text-surface-400 hover:text-white transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button
            onClick={() => scroll('right')}
            className="p-1.5 rounded-lg bg-surface-800 hover:bg-surface-700 text-surface-400 hover:text-white transition-colors"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Scrollable row */}
      <div
        ref={scrollRef}
        className="flex gap-4 overflow-x-auto scrollbar-hide pb-2"
        style={{ scrollbarWidth: 'none' }}
      >
        {items.map((item) => (
          <div key={item.movie_id} className="flex-shrink-0 w-[180px]">
            <MovieCard
              movie={{
                movie_id: item.movie_id,
                title: item.title,
                genres: item.genres,
                year: item.year,
                poster_url: item.poster_url,
                avg_rating: item.avg_rating,
                rating_count: item.rating_count,
              }}
            />
          </div>
        ))}
      </div>
    </section>
  )
}

export default RecommendationCarousel
