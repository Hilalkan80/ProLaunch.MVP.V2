/**
 * Auth context provider
 */
import React, { createContext, useContext, useState } from 'react'
import { AuthService } from '../lib/auth/auth-service'
import type { User } from '../lib/auth/types'

interface AuthContextValue {
  isAuthenticated: boolean
  user: User | null
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  refresh: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue>({
  isAuthenticated: false,
  user: null,
  login: async () => {},
  logout: async () => {},
  refresh: async () => {}
})

export const useAuth = () => useContext(AuthContext)

interface AuthProviderProps {
  children: React.ReactNode
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [authService] = useState(() => new AuthService())
  const [isAuthenticated, setIsAuthenticated] = useState(authService.isAuthenticated())
  const [user, setUser] = useState<User | null>(authService.getCurrentUser())

  const login = async (email: string, password: string) => {
    const response = await authService.login({ email, password })
    setIsAuthenticated(true)
    setUser(response.user)
  }

  const logout = async () => {
    await authService.logout()
    setIsAuthenticated(false)
    setUser(null)
  }

  const refresh = async () => {
    await authService.refreshTokens()
    setUser(authService.getCurrentUser())
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, user, login, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  )
}