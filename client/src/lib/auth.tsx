import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { api, type User } from './api'

type Auth = {
  user: User | null | undefined // undefined = still loading
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<Auth>(null!)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>()

  useEffect(() => {
    api('/auth/csrf/')
      .then(() => api<User>('/auth/me/'))
      .then(setUser, () => setUser(null))
  }, [])

  const login = async (email: string, password: string) => {
    setUser(await api<User>('/auth/login/', { body: { email, password } }))
  }
  const logout = async () => {
    await api('/auth/logout/', { method: 'POST' })
    setUser(null)
  }
  return <AuthContext.Provider value={{ user, login, logout }}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)

/** Logged-out visitors go to /login and come back afterwards (PRD S3 AC). */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const location = useLocation()
  if (user === undefined) return null
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return children
}
