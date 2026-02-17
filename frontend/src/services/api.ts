import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api/v1`
  : '/api/v1'

const api = axios.create({
  baseURL: API_BASE,
  timeout: 90_000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ─── Auth interceptor ──────────────────────────────────────────────────────
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ─── Types ─────────────────────────────────────────────────────────────────

export interface Movie {
  movie_id: number
  title: string
  genres: string[] | null
  year: number | null
  imdb_id?: string | null
  tmdb_id?: number | null
  poster_url?: string | null
  avg_rating: number
  rating_count: number
}

export interface MovieDetail extends Movie {
  created_at: string
  updated_at: string
}

export interface MovieListResponse {
  movies: Movie[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface RecommendationItem {
  movie_id: number
  title: string
  genres: string[] | null
  year: number | null
  poster_url: string | null
  avg_rating: number
  rating_count: number
  predicted_rating: number
  explanation: string
  confidence: number
  model_source: string
}

export interface RecommendationResponse {
  user_id: number
  recommendations: RecommendationItem[]
  strategy: string
  generated_at: string
  latency_ms: number
  cached: boolean
}

export interface SimilarMoviesResponse {
  movie_id: number
  title: string
  similar_movies: RecommendationItem[]
  generated_at: string
  latency_ms: number
}

export interface SearchParams {
  query?: string
  genre?: string
  year_min?: number
  year_max?: number
  min_rating?: number
  sort_by?: string
  page?: number
  page_size?: number
}

export interface RatingResponse {
  user_id: number
  movie_id: number
  rating: number
  timestamp: string
}

export interface RatingWithMovie extends RatingResponse {
  movie_title: string
  movie_genres: string[] | null
  movie_year: number | null
  movie_poster_url: string | null
  movie_avg_rating: number
}

export interface RatingWithMovieItem {
  user_id: number
  movie_id: number
  rating: number
  timestamp: string
  movie_title: string
  movie_genres: string[] | null
  movie_year: number | null
  movie_poster_url: string | null
  movie_avg_rating: number
}

export interface UserRatingsResponse {
  user_id: number
  ratings: RatingWithMovieItem[]
  total: number
  page: number
  page_size: number
}

export interface UserRatingStats {
  total_rated: number
  avg_rating: number
  rating_distribution: Record<string, number>
  genre_breakdown: Record<string, number>
}

export interface DiscoverItem {
  movie_id: number
  title: string
  genres: string[] | null
  year: number | null
  poster_url: string | null
  avg_rating: number
  rating_count: number
  relevance_score: number
  matched_tags: string[]
}

export interface DiscoverResponse {
  query: string
  items: DiscoverItem[]
  total: number
  latency_ms: number
}

export interface UserProfile {
  user_id: number
  username: string | null
  email?: string | null
  avatar_url?: string | null
  rating_count: number
  avg_rating: number
}

export interface AuthResponse {
  user: UserProfile
  access_token: string
}

// ─── API functions ─────────────────────────────────────────────────────────

export const movieApi = {
  search: async (params: SearchParams): Promise<MovieListResponse> => {
    const { data } = await api.get('/movies', { params })
    return data
  },

  getById: async (movieId: number): Promise<MovieDetail> => {
    const { data } = await api.get(`/movies/${movieId}`)
    return data
  },

  getPopular: async (limit = 20, genre?: string): Promise<Movie[]> => {
    const { data } = await api.get('/movies/popular', { params: { limit, genre } })
    return data
  },
}

export const recommendationApi = {
  getForUser: async (userId: number, limit = 20): Promise<RecommendationResponse> => {
    const { data } = await api.get(`/recommendations/${userId}`, { params: { limit, explain: true } })
    return data
  },

  getSimilar: async (movieId: number, limit = 10): Promise<SimilarMoviesResponse> => {
    const { data } = await api.get(`/recommendations/similar/${movieId}`, { params: { limit } })
    return data
  },
}

export const userApi = {
  getProfile: async (userId: number): Promise<UserProfile> => {
    const { data } = await api.get(`/users/${userId}`)
    return data
  },

  getRatingForMovie: async (userId: number, movieId: number): Promise<RatingResponse | null> => {
    const { data } = await api.get(`/users/${userId}/ratings/movie/${movieId}`)
    return data
  },

  getRatings: async (
    userId: number,
    page = 1,
    pageSize = 20,
    sortBy = 'date_desc',
  ): Promise<UserRatingsResponse> => {
    const { data } = await api.get(`/users/${userId}/ratings`, {
      params: { page, page_size: pageSize, sort_by: sortBy },
    })
    return data
  },

  getRatingStats: async (userId: number): Promise<UserRatingStats> => {
    const { data } = await api.get(`/users/${userId}/ratings/stats`)
    return data
  },

  rateMovie: async (userId: number, movieId: number, rating: number): Promise<RatingResponse> => {
    const { data } = await api.post(`/users/${userId}/ratings`, { movie_id: movieId, rating })
    return data
  },

  deleteRating: async (userId: number, movieId: number): Promise<void> => {
    await api.delete(`/users/${userId}/ratings/${movieId}`)
  },
}

export const discoverApi = {
  search: async (query: string, limit = 20): Promise<DiscoverResponse> => {
    const { data } = await api.get('/discover', { params: { q: query, limit } })
    return data
  },
}

export const authApi = {
  googleLogin: async (idToken: string): Promise<AuthResponse> => {
    const { data } = await api.post('/auth/google', { id_token: idToken })
    return data
  },

  getMe: async (): Promise<UserProfile> => {
    const { data } = await api.get('/auth/me')
    return data
  },
}

export const healthApi = {
  check: async () => {
    const { data } = await api.get('/health')
    return data
  },
}

export default api
