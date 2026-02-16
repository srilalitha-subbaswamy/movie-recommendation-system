interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  text?: string
}

function LoadingSpinner({ size = 'md', text }: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'w-5 h-5',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  }

  return (
    <div className="flex flex-col items-center justify-center py-12">
      <div
        className={`${sizeClasses[size]} border-2 border-surface-700 border-t-primary-500 rounded-full animate-spin`}
      />
      {text && <p className="mt-3 text-sm text-surface-400">{text}</p>}
    </div>
  )
}

export default LoadingSpinner
