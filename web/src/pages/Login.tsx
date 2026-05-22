import { FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'
import { useAuth } from '../App'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { data } = await api.post('/auth/login', { username, password })
      login({ token: data.access_token, userId: data.user_id })
      navigate('/chat')
    } catch (err: any) {
      setError(err.response?.data?.detail ?? 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-snow px-4">
      <div className="w-full max-w-sm">

        <div className="text-center mb-10">
          <p className="text-xs text-pewter uppercase tracking-widest mb-3">Excelsis 360</p>
          <h1 className="text-2xl font-semibold text-carbon tracking-tight">Data Analyst</h1>
        </div>

        <form onSubmit={submit} className="space-y-4">
          {error && (
            <p className="text-danger text-sm text-center bg-danger/5 border border-danger/20 rounded-[10px] px-3 py-2">
              {error}
            </p>
          )}

          <div>
            <label className="block text-xs text-pewter mb-1.5">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required autoFocus
              placeholder="admin"
              className="w-full bg-fog border border-arctic-mist rounded-input px-5 py-3 text-sm text-carbon placeholder-pewter focus:outline-none focus:ring-2 focus:ring-link-blue"
            />
          </div>

          <div>
            <label className="block text-xs text-pewter mb-1.5">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="••••••••"
              className="w-full bg-fog border border-arctic-mist rounded-input px-5 py-3 text-sm text-carbon placeholder-pewter focus:outline-none focus:ring-2 focus:ring-link-blue"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-carbon text-white disabled:opacity-40 font-medium py-3 rounded-pill text-sm hover:opacity-90 transition-opacity mt-2"
          >
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

      </div>
    </div>
  )
}
