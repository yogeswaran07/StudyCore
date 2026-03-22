import { createContext, useContext, useState, useEffect } from 'react'
import axios from 'axios'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(() => localStorage.getItem('tf_token'))
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
    } else {
      delete axios.defaults.headers.common['Authorization']
    }
  }, [token])

  useEffect(() => {
    const stored = localStorage.getItem('tf_user')
    if (stored && token) {
      try {
        setUser(JSON.parse(stored))
      } catch {
        localStorage.removeItem('tf_user')
      }
    }
    setLoading(false)
  }, [token])

  const login = (userData, authToken) => {
    setToken(authToken)
    setUser(userData)
    localStorage.setItem('tf_token', authToken)
    localStorage.setItem('tf_user', JSON.stringify(userData))
    axios.defaults.headers.common['Authorization'] = `Bearer ${authToken}`
  }

  const logout = () => {
    setToken(null)
    setUser(null)
    localStorage.removeItem('tf_token')
    localStorage.removeItem('tf_user')
    delete axios.defaults.headers.common['Authorization']
  }

  const updateUser = (updatedUser) => {
    setUser(updatedUser)
    localStorage.setItem('tf_user', JSON.stringify(updatedUser))
  }

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout, updateUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
