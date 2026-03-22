import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { io } from 'socket.io-client'
import { useAuth } from '../context/AuthContext'
import TaskCard from '../components/TaskCard'
import MemberList from '../components/MemberList'
import CreateTaskModal from '../components/CreateTaskModal'
import ProgressBar from '../components/ProgressBar'

export default function Dashboard() {
  const { user, updateUser } = useAuth()
  const navigate = useNavigate()

  const [team, setTeam] = useState(null)
  const [tasks, setTasks] = useState([])
  const [loadingTeam, setLoadingTeam] = useState(true)
  const [showCreateTask, setShowCreateTask] = useState(false)
  const [notification, setNotification] = useState(null)
  const socketRef = useRef(null)

  const showNotif = (msg, type = 'info') => {
    setNotification({ msg, type })
    setTimeout(() => setNotification(null), 4000)
  }

  const fetchTeam = useCallback(async () => {
    try {
      const { data } = await axios.get('/api/teams/me')
      setTeam(data)
    } catch {
      setTeam(null)
    }
  }, [])

  const fetchTasks = useCallback(async () => {
    try {
      const { data } = await axios.get('/api/tasks')
      setTasks(data)
    } catch {
      setTasks([])
    }
  }, [])

  useEffect(() => {
    if (!user?.teamId) {
      setLoadingTeam(false)
      return
    }
    Promise.all([fetchTeam(), fetchTasks()]).finally(() => setLoadingTeam(false))
  }, [user?.teamId, fetchTeam, fetchTasks])

  // Socket.io real-time updates
  useEffect(() => {
    if (!user?.teamId) return

    const socket = io('/', { withCredentials: true })
    socketRef.current = socket

    socket.on('connect', () => {
      socket.emit('join:team', user.teamId.toString())
    })

    socket.on('task:created', (task) => {
      setTasks((prev) => [...prev, task])
      showNotif('A new task has been created!', 'info')
    })

    socket.on('task:updated', (updated) => {
      setTasks((prev) => prev.map((t) => (t._id === updated._id ? updated : t)))
    })

    socket.on('task:unlocked', (unlocked) => {
      setTasks((prev) => prev.map((t) => (t._id === unlocked._id ? unlocked : t)))
      showNotif(`🎉 Task "${unlocked.title}" is now unlocked!`, 'success')
    })

    socket.on('task:deleted', ({ taskId }) => {
      setTasks((prev) => prev.filter((t) => t._id !== taskId))
    })

    return () => {
      socket.emit('leave:team', user.teamId.toString())
      socket.disconnect()
    }
  }, [user?.teamId])

  const handleMarkComplete = async (taskId) => {
    try {
      await axios.patch(`/api/tasks/${taskId}/complete`)
      await fetchTasks()
    } catch (err) {
      showNotif(err.response?.data?.message || 'Failed to mark task complete', 'error')
    }
  }

  const handleTaskCreated = (task) => {
    setTasks((prev) => [...prev, task])
    setShowCreateTask(false)
  }

  const handleDeleteTask = async (taskId) => {
    try {
      await axios.delete(`/api/tasks/${taskId}`)
      setTasks((prev) => prev.filter((t) => t._id !== taskId))
    } catch (err) {
      showNotif(err.response?.data?.message || 'Failed to delete task', 'error')
    }
  }

  // Redirect to team-setup if user has no team
  if (!loadingTeam && !user?.teamId) {
    navigate('/team-setup')
    return null
  }

  if (loadingTeam) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-8 h-8 rounded-full border-4 border-primary-600 border-t-transparent animate-spin" />
      </div>
    )
  }

  const activeTask = tasks.find((t) => t.status === 'active')
  const completedTasks = tasks.filter((t) => t.status === 'completed')
  const lockedTasks = tasks.filter((t) => t.status === 'locked')
  const isLeader = user?.role === 'leader'
  const memberCount = team?.members?.length || 0
  const activeCompletedCount = activeTask?.completedBy?.length || 0
  const userCompletedActive = activeTask?.completedBy?.some(
    (u) => (u._id || u) === user?._id
  )

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      {/* Notification */}
      {notification && (
        <div
          className={`fixed top-20 right-4 z-50 rounded-xl px-5 py-3 text-sm font-medium shadow-lg transition-all animate-bounce-once ${
            notification.type === 'success'
              ? 'bg-teal-600 text-white'
              : notification.type === 'error'
              ? 'bg-rose-600 text-white'
              : 'bg-primary-700 text-white'
          }`}
        >
          {notification.msg}
        </div>
      )}

      {/* Header */}
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">{team?.name}</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            {isLeader ? 'Leader dashboard' : 'Member dashboard'} · {memberCount} member{memberCount !== 1 ? 's' : ''}
          </p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          {/* Invite code */}
          <div className="flex items-center gap-2 rounded-lg border border-dashed border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900">
            <span className="text-xs text-slate-500 dark:text-slate-400">Invite code:</span>
            <span className="font-mono text-sm font-semibold text-primary-700 dark:text-primary-400 tracking-widest">
              {team?.inviteCode}
            </span>
            <button
              onClick={() => {
                navigator.clipboard.writeText(team?.inviteCode || '')
                showNotif('Invite code copied!', 'success')
              }}
              className="text-slate-400 hover:text-primary-600 transition-colors"
              title="Copy invite code"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
            </button>
          </div>

          {isLeader && (
            <button onClick={() => setShowCreateTask(true)} className="btn-primary">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              New task
            </button>
          )}
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 mb-8">
        <StatCard label="Total Tasks" value={tasks.length} icon="📋" />
        <StatCard label="Completed" value={completedTasks.length} icon="✅" />
        <StatCard label="In Progress" value={activeTask ? 1 : 0} icon="⚡" />
        <StatCard label="Locked" value={lockedTasks.length} icon="🔒" />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left: Tasks */}
        <div className="lg:col-span-2 space-y-4">
          <h2 className="text-base font-semibold text-slate-700 dark:text-slate-300">
            Task Sequence
          </h2>

          {tasks.length === 0 ? (
            <div className="card text-center py-12">
              <div className="text-4xl mb-3">📭</div>
              <p className="text-slate-500 dark:text-slate-400 text-sm">No tasks yet.</p>
              {isLeader && (
                <button onClick={() => setShowCreateTask(true)} className="btn-primary mt-4 text-sm">
                  Create first task
                </button>
              )}
            </div>
          ) : (
            tasks.map((task) => (
              <TaskCard
                key={task._id}
                task={task}
                user={user}
                memberCount={memberCount}
                onComplete={handleMarkComplete}
                onDelete={isLeader ? handleDeleteTask : null}
              />
            ))
          )}
        </div>

        {/* Right: Active task progress + members */}
        <div className="space-y-4">
          {activeTask && (
            <div className="card">
              <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
                Current Task Progress
              </h3>
              <p className="text-base font-semibold text-slate-900 dark:text-white mb-1">
                {activeTask.title}
              </p>
              <ProgressBar completed={activeCompletedCount} total={memberCount} />
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">
                {activeCompletedCount}/{memberCount} members completed
              </p>
              {!userCompletedActive && (
                <button
                  onClick={() => handleMarkComplete(activeTask._id)}
                  className="btn-primary w-full mt-4 text-sm"
                >
                  Mark as complete
                </button>
              )}
              {userCompletedActive && (
                <div className="mt-4 rounded-lg bg-teal-50 border border-teal-200 px-4 py-2 text-sm text-teal-700 dark:bg-teal-900/20 dark:border-teal-800 dark:text-teal-400 text-center">
                  ✓ You&apos;ve completed this task
                </div>
              )}
            </div>
          )}

          <div className="card">
            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
              Team Members
            </h3>
            <MemberList
              members={team?.members || []}
              leaderId={team?.leaderId}
              activeTask={activeTask}
            />
          </div>

          {/* Leader analytics */}
          {isLeader && tasks.length > 0 && (
            <div className="card">
              <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
                Progress Overview
              </h3>
              <div className="space-y-2">
                <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400">
                  <span>Overall completion</span>
                  <span>{completedTasks.length}/{tasks.length} tasks</span>
                </div>
                <ProgressBar completed={completedTasks.length} total={tasks.length} />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Create Task Modal */}
      {showCreateTask && (
        <CreateTaskModal
          onClose={() => setShowCreateTask(false)}
          onCreated={handleTaskCreated}
        />
      )}
    </div>
  )
}

function StatCard({ label, value, icon }) {
  return (
    <div className="card flex items-center gap-3">
      <span className="text-2xl">{icon}</span>
      <div>
        <p className="text-xl font-bold text-slate-900 dark:text-white">{value}</p>
        <p className="text-xs text-slate-500 dark:text-slate-400">{label}</p>
      </div>
    </div>
  )
}
