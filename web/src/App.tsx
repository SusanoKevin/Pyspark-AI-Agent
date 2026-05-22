import { createContext, useContext, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Toaster } from 'sonner'
import Login from './pages/Login'
import Chat from './pages/Chat'
import Dashboard from './pages/Dashboard'
import Users from './pages/Users'
import ProtectedRoute from './components/ProtectedRoute'
import { AuthUser } from './types'

interface AuthCtx {
  user: AuthUser | null
  login: (u: AuthUser) => void
  logout: () => void
}

export const AuthContext = createContext<AuthCtx>({
  user: null, login: () => {}, logout: () => {},
})
export const useAuth = () => useContext(AuthContext)

function loadUser(): AuthUser | null {
  const token  = localStorage.getItem('token')
  const userId = localStorage.getItem('userId')
  if (!token || !userId) return null
  return { token, userId }
}

export default function App() {
  const [user, setUser] = useState<AuthUser | null>(loadUser)

  const login = (u: AuthUser) => {
    localStorage.setItem('token',  u.token)
    localStorage.setItem('userId', u.userId)
    setUser(u)
  }

  const logout = () => {
    localStorage.clear()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      <Toaster position="bottom-right" theme="dark" richColors />
      <BrowserRouter>
        <Routes>
          <Route path="/login"     element={<Login />} />
          <Route path="/"          element={<Navigate to="/chat" replace />} />
          <Route path="/chat"      element={<ProtectedRoute><Chat /></ProtectedRoute>} />
          <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/users"     element={<ProtectedRoute><Users /></ProtectedRoute>} />
        </Routes>
      </BrowserRouter>
    </AuthContext.Provider>
  )
}
