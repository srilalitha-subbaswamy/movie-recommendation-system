import { useState } from 'react'
import { Star } from 'lucide-react'

interface RatingStarsProps {
  rating: number
  maxRating?: number
  size?: 'sm' | 'md' | 'lg'
  showValue?: boolean
  interactive?: boolean
  onRate?: (rating: number) => void
}

function RatingStars({
  rating,
  maxRating = 5,
  size = 'md',
  showValue = true,
  interactive = false,
  onRate,
}: RatingStarsProps) {
  const [hoverRating, setHoverRating] = useState<number | null>(null)

  const sizeClasses = {
    sm: 'w-3.5 h-3.5',
    md: 'w-5 h-5',
    lg: 'w-6 h-6',
  }

  const displayRating = hoverRating ?? rating

  const stars = Array.from({ length: maxRating }, (_, i) => {
    const filled = i < Math.floor(displayRating)
    const half = !filled && i < displayRating
    return { filled, half, index: i }
  })

  const handleClick = (starIndex: number) => {
    if (!interactive || !onRate) return
    onRate(starIndex + 1)
  }

  const handleMouseEnter = (starIndex: number) => {
    if (!interactive) return
    setHoverRating(starIndex + 1)
  }

  const handleMouseLeave = () => {
    if (!interactive) return
    setHoverRating(null)
  }

  return (
    <div className="flex items-center gap-1" onMouseLeave={handleMouseLeave}>
      {stars.map((star) => (
        <Star
          key={star.index}
          className={`${sizeClasses[size]} transition-colors ${
            star.filled
              ? 'text-yellow-400 fill-yellow-400'
              : star.half
                ? 'text-yellow-400 fill-yellow-400/50'
                : interactive && hoverRating !== null
                  ? 'text-surface-500'
                  : 'text-surface-600'
          } ${interactive ? 'cursor-pointer hover:scale-110 transition-transform' : ''}`}
          onClick={() => handleClick(star.index)}
          onMouseEnter={() => handleMouseEnter(star.index)}
        />
      ))}
      {showValue && (
        <span className="ml-1 text-sm font-semibold text-surface-300">
          {hoverRating !== null ? hoverRating.toFixed(1) : rating.toFixed(1)}
        </span>
      )}
    </div>
  )
}

export default RatingStars
