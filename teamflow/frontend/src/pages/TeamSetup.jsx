import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { useAuth } from '../context/AuthContext'

export default function TeamSetup() {
  const { user, updateUser } = useAuth()
  const navigate = useNavigate()
  const [tab, setTab] = useState('create')
  const [teamName, setTeamName] = useState('')
  const [inviteCode, setInviteCode] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  // If already in a team, redirect
  if (user?.teamId) {
    navigate('/dashboard')
    return null
  }

  const handleCreate = async (e) => {
    e.preventDefault()
    setError('')
    if (!teamName.trim()) return setError('Team name is required')
    setLoading(true)
    try {
      await axios.post('/api/teams', { name: teamName.trim() })
      const { data: updated } = await axios.get('/api/auth/me').catch(async () => {
        // Fallback: re-fetch via teams/me
        const { data: team } = await axios.get('/api/teams/me')
        return { data: { ...user, teamId: team._id, role: 'leader' } }
      })
      updateUser({ ...user, teamId: updated.teamId || updated._id, role: 'leader' })
      navigate('/dashboard')
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to create team')
    } finally {
      setLoading(false)
    }
  }

  const handleJoin = async (e) => {
    e.preventDefault()
    setError('')
    if (!inviteCode.trim()) return setError('Invite code is required')
    setLoading(true)
    try {
      await axios.post('/api/teams/join', { inviteCode: inviteCode.trim() })
      const { data: team } = await axios.get('/api/teams/me')
      updateUser({ ...user, teamId: team._id, role: 'member' })
      navigate('/dashboard')
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to join team')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-[calc(100vh-64px)] items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Get started with a team</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Create a new team or join an existing one
          </p>
        </div>

        {/* Tabs */}
        <div className="flex rounded-xl bg-slate-100 p-1 dark:bg-slate-800 mb-6">
          {['create', 'join'].map((t) => (
            <button
              key={t}
              onClick={() => { setTab(t); setError('') }}
              className={`flex-1 rounded-lg py-2 text-sm font-medium transition-all ${
                tab === t
                  ? 'bg-white shadow text-primary-800 dark:bg-slate-700 dark:text-primary-300'
                  : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
              }`}
            >
              {t === 'create' ? 'Create team' : 'Join team'}
            </button>
          ))}
        </div>

        <div className="card">
          {error && (
            <div className="mb-4 rounded-lg bg-rose-50 border border-rose-200 px-4 py-3 text-sm text-rose-700 dark:bg-rose-900/20 dark:border-rose-800 dark:text-rose-400">
              {error}
            </div>
          )}

          {tab === 'create' ? (
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label htmlFor="teamName" className="label">Team name</label>
                <input
                  id="teamName"
                  type="text"
                  className="input"
                  placeholder="e.g. Alpha Squad"
                  value={teamName}
                  onChange={(e) => setTeamName(e.target.value)}
                />
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                You&apos;ll be the team leader and receive an invite code to share with members.
              </p>
              <button type="submit" disabled={loading} className="btn-primary w-full">
                {loading ? 'Creating...' : 'Create team'}
              </button>
            </form>
          ) : (
            <form onSubmit={handleJoin} className="space-y-4">
              <div>
                <label htmlFor="inviteCode" className="label">Invite code</label>
                <input
                  id="inviteCode"
                  type="text"
                  className="input uppercase"
                  placeholder="e.g. A1B2C3D4"
                  value={inviteCode}
                  onChange={(e) => setInviteCode(e.target.value.toUpperCase())}
                  maxLength={8}
                />
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Ask your team leader for the 8-character invite code.
              </p>
              <button type="submit" disabled={loading} className="btn-primary w-full">
                {loading ? 'Joining...' : 'Join team'}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
