import { useQuery } from '@tanstack/react-query'
import { Sparkles, TrendingUp, Zap } from 'lucide-react'
import { useUser } from '../context/UserContext'
import RecommendationCarousel from '../components/RecommendationCarousel'
import MovieGrid from '../components/MovieGrid'
import LoadingSpinner from '../components/LoadingSpinner'
import { movieApi, recommendationApi } from '../services/api'

function HomePage() {
  const { currentUser } = useUser()

  const {
    data: recommendations,
    isLoading: recsLoading,
    error: recsError,
  } = useQuery({
    queryKey: ['recommendations', currentUser.id],
    queryFn: () => recommendationApi.getForUser(currentUser.id),
    retry: 1,
  })

  const {
    data: popularMovies,
    isLoading: popularLoading,
  } = useQuery({
    queryKey: ['popular-movies'],
    queryFn: () => movieApi.getPopular(18),
    retry: 1,
  })

  return (
    <div>
      {/* Hero */}
      <section className="mb-12">
        <div className="relative bg-gradient-to-br from-primary-950 via-surface-900 to-surface-950 rounded-2xl p-8 md:p-12 overflow-hidden">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_50%,rgba(239,68,68,0.1),transparent_50%)]" />
          <div className="relative z-10">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles className="w-5 h-5 text-primary-400" />
              <span className="text-sm font-medium text-primary-400">AI-Powered Recommendations</span>
            </div>
            <h1 className="text-3xl md:text-4xl font-bold text-white mb-3">
              Discover Your Next
              <span className="text-primary-500"> Favorite Film</span>
            </h1>
            <p className="text-surface-400 max-w-xl text-lg">
              Personalized movie recommendations powered by collaborative filtering
              and neural networks. Built with Spark ALS, PyTorch, and FastAPI.
            </p>

            {/* Tech badges */}
            <div className="flex flex-wrap gap-2 mt-6">
              {['Spark ALS', 'FastAPI', 'PostgreSQL', 'Redis', 'React'].map((tech) => (
                <span
                  key={tech}
                  className="text-xs font-medium bg-surface-800/80 text-surface-300 px-2.5 py-1 rounded-full border border-surface-700"
                >
                  {tech}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Personalized Recommendations */}
      <section className="mb-12">
        <div className="flex items-center gap-2 mb-2">
          <Zap className="w-5 h-5 text-yellow-400" />
          <h2 className="text-xl font-bold text-white">For You, {currentUser.name}</h2>
        </div>

        {recsLoading && <LoadingSpinner text="Generating recommendations... (may take a moment if the server is waking up)" />}

        {recsError && (
          <div className="bg-surface-800 rounded-xl p-6 text-center">
            <p className="text-surface-400">
              Could not load recommendations. The server may be waking up from sleep.
            </p>
            <p className="text-xs text-surface-500 mt-2">
              Free-tier services spin down after inactivity. Please refresh in ~30 seconds.
            </p>
          </div>
        )}

        {recommendations && (
          <RecommendationCarousel
            title="Recommended for You"
            subtitle={
              recommendations.strategy === 'collaborative'
                ? `ALS collaborative filtering · Based on ${currentUser.ratingCount} ratings`
                : recommendations.strategy === 'content_based'
                ? `Content-based · Building profile from ${currentUser.ratingCount} ratings`
                : `Popular movies · Rate films to get personalized picks`
            }
            items={recommendations.recommendations}
            strategy={recommendations.strategy}
            latencyMs={recommendations.latency_ms}
          />
        )}
      </section>

      {/* Popular Movies */}
      <section>
        <div className="flex items-center gap-2 mb-6">
          <TrendingUp className="w-5 h-5 text-green-400" />
          <h2 className="text-xl font-bold text-white">Trending Now</h2>
        </div>

        {popularLoading && <LoadingSpinner text="Loading movies..." />}

        {popularMovies && <MovieGrid movies={popularMovies} />}
      </section>
    </div>
  )
}

export default HomePage
