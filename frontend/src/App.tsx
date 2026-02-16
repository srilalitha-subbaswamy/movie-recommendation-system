import { Routes, Route } from 'react-router-dom'
import { UserProvider } from './context/UserContext'
import Navbar from './components/Navbar'
import HomePage from './pages/HomePage'
import BrowsePage from './pages/BrowsePage'
import DiscoverPage from './pages/DiscoverPage'
import MovieDetailPage from './pages/MovieDetailPage'
import MyRatingsPage from './pages/MyRatingsPage'
import ProfilePage from './pages/ProfilePage'

function App() {
  return (
    <UserProvider>
      <div className="min-h-screen bg-surface-950">
        <Navbar />
        <main className="container mx-auto px-4 py-8">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/discover" element={<DiscoverPage />} />
            <Route path="/browse" element={<BrowsePage />} />
            <Route path="/movie/:movieId" element={<MovieDetailPage />} />
            <Route path="/my-ratings" element={<MyRatingsPage />} />
            <Route path="/profile" element={<ProfilePage />} />
          </Routes>
        </main>
      </div>
    </UserProvider>
  )
}

export default App
