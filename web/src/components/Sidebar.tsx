import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../App'

const link = ({ isActive }: { isActive: boolean }) =>
  `flex items-center px-3 py-2.5 text-sm rounded-[10px] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-link-blue focus-visible:ring-offset-1 ${
    isActive
      ? 'bg-arctic-mist text-carbon font-medium'
      : 'text-pewter hover:text-carbon hover:bg-arctic-mist'
  }`

export default function Sidebar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  return (
    <aside className="w-52 min-h-screen bg-fog border-r border-arctic-mist flex flex-col">
      <div className="px-5 py-6 border-b border-arctic-mist">
        <p className="text-xs text-pewter uppercase tracking-widest mb-1">Excelsis 360</p>
        <p className="text-sm text-carbon font-semibold">Data Analyst</p>
      </div>

      <nav className="flex-1 py-4 px-3 space-y-0.5">
        <NavLink to="/chat"      className={link}>Chat</NavLink>
        <NavLink to="/dashboard" className={link}>Dashboard</NavLink>
        <NavLink to="/users"     className={link}>Users</NavLink>
      </nav>

      <div className="p-5 border-t border-arctic-mist">
        <p className="text-xs text-carbon font-medium truncate mb-4">{user?.userId}</p>
        <button
          onClick={() => { logout(); navigate('/login') }}
          className="text-sm text-pewter hover:text-carbon transition-colors text-left rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-link-blue focus-visible:ring-offset-1"
        >
          Sign out →
        </button>
      </div>
    </aside>
  )
}
