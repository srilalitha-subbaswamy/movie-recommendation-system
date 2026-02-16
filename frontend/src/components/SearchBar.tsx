import { useState, useEffect } from 'react'
import { Search, X } from 'lucide-react'

interface SearchBarProps {
  onSearch: (query: string) => void
  placeholder?: string
  initialValue?: string
}

function SearchBar({ onSearch, placeholder = 'Search movies...', initialValue = '' }: SearchBarProps) {
  const [value, setValue] = useState(initialValue)

  useEffect(() => {
    setValue(initialValue)
  }, [initialValue])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSearch(value.trim())
  }

  const handleClear = () => {
    setValue('')
    onSearch('')
  }

  return (
    <form onSubmit={handleSubmit} className="relative w-full max-w-xl">
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-surface-400" />
      <input
        type="text"
        value={value}
        onChange={(e) => {
          const newVal = e.target.value
          setValue(newVal)
          if (newVal.trim() === '') {
            onSearch('')
          }
        }}
        placeholder={placeholder}
        className="input w-full pl-10 pr-10"
      />
      {value && (
        <button
          type="button"
          onClick={handleClear}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-surface-400 hover:text-surface-200"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </form>
  )
}

export default SearchBar
