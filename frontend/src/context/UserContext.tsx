import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'
import { authApi } from '../services/api'

interface UserInfo {
  id: number
  name: string
  ratingCount: number
}

interface AuthUser {
  id: number
  name: string
  email: string | null
  avatar_url: string | null
  ratingCount: number
}

const DEMO_USERS: UserInfo[] = [
  { id: 414, name: 'Alice', ratingCount: 1062 },
  { id: 610, name: 'Bob', ratingCount: 639 },
  { id: 249, name: 'Charlie', ratingCount: 643 },
  { id: 298, name: 'Diana', ratingCount: 595 },
  { id: 608, name: 'Eve', ratingCount: 753 },
  { id: 217, name: 'Frank', ratingCount: 291 },
  { id: 226, name: 'Grace', ratingCount: 394 },
]

interface UserContextType {
  currentUser: UserInfo
  users: UserInfo[]
  setCurrentUser: (userId: number) => void
  authUser: AuthUser | null
  login: (idToken: string) => Promise<void>
  logout: () => void
  isAuthenticated: boolean
}

const UserContext = createContext<UserContextType | null>(null)

export function UserProvider({ children }: { children: ReactNode }) {
  const [demoUser, setDemoUser] = useState<UserInfo>(DEMO_USERS[0])
  const [authUser, setAuthUser] = useState<AuthUser | null>(null)

  // Check for existing token on mount
  useEffect(() => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      authApi
        .getMe()
        .then((user) => {
          setAuthUser({
            id: user.user_id,
            name: user.username || user.email || 'User',
            email: user.email || null,
            avatar_url: user.avatar_url || null,
            ratingCount: user.rating_count,
          })
        })
        .catch(() => {
          // Token expired or invalid
          localStorage.removeItem('auth_token')
        })
    }
  }, [])

  const setCurrentUser = (userId: number) => {
    const user = DEMO_USERS.find((u) => u.id === userId)
    if (user) setDemoUser(user)
  }

  const login = async (idToken: string) => {
    const response = await authApi.googleLogin(idToken)
    localStorage.setItem('auth_token', response.access_token)
    setAuthUser({
      id: response.user.user_id,
      name: response.user.username || response.user.email || 'User',
      email: response.user.email || null,
      avatar_url: response.user.avatar_url || null,
      ratingCount: response.user.rating_count,
    })
  }

  const logout = () => {
    localStorage.removeItem('auth_token')
    setAuthUser(null)
  }

  // Active user: auth user takes priority over demo user
  const currentUser: UserInfo = authUser
    ? { id: authUser.id, name: authUser.name, ratingCount: authUser.ratingCount }
    : demoUser

  return (
    <UserContext.Provider
      value={{
        currentUser,
        users: DEMO_USERS,
        setCurrentUser,
        authUser,
        login,
        logout,
        isAuthenticated: !!authUser,
      }}
    >
      {children}
    </UserContext.Provider>
  )
}

export function useUser(): UserContextType {
  const context = useContext(UserContext)
  if (!context) {
    throw new Error('useUser must be used within a UserProvider')
  }
  return context
}
