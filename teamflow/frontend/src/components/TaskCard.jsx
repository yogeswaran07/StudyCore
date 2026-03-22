import ProgressBar from './ProgressBar'

const statusConfig = {
  active: { label: 'Active', className: 'badge-active' },
  completed: { label: 'Completed', className: 'badge-completed' },
  locked: { label: 'Locked', className: 'badge-locked' },
}

export default function TaskCard({ task, user, memberCount, onComplete, onDelete }) {
  const config = statusConfig[task.status] || statusConfig.locked
  const completedCount = task.completedBy?.length || 0
  const userCompleted = task.completedBy?.some(
    (u) => (u._id || u).toString() === user?._id
  )
  const isActive = task.status === 'active'
  const isLocked = task.status === 'locked'

  return (
    <div
      className={`card transition-all hover:shadow-card-hover ${
        isLocked ? 'opacity-60' : ''
      } ${isActive ? 'ring-2 ring-primary-500/30' : ''}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 flex-1 min-w-0">
          {/* Order badge */}
          <div
            className={`flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center text-xs font-bold ${
              task.status === 'completed'
                ? 'bg-primary-100 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300'
                : task.status === 'active'
                ? 'bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300'
                : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'
            }`}
          >
            {task.status === 'completed' ? '✓' : isLocked ? '🔒' : task.order}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <h3
                className={`text-sm font-semibold ${
                  task.status === 'completed'
                    ? 'line-through text-slate-400 dark:text-slate-500'
                    : 'text-slate-900 dark:text-white'
                }`}
              >
                Task {task.order}: {task.title}
              </h3>
              <span className={config.className}>{config.label}</span>
            </div>

            {task.description && (
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 leading-relaxed">
                {task.description}
              </p>
            )}

            {isActive && (
              <div className="mt-3">
                <ProgressBar completed={completedCount} total={memberCount} />
                <p className="text-xs text-slate-400 mt-1">
                  {completedCount}/{memberCount} members completed
                </p>
              </div>
            )}

            {task.status === 'completed' && (
              <p className="text-xs text-primary-600 dark:text-primary-400 mt-1">
                All {memberCount} members completed ✓
              </p>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {isActive && !userCompleted && (
            <button
              onClick={() => onComplete(task._id)}
              className="btn-primary text-xs px-3 py-1.5"
            >
              Complete
            </button>
          )}
          {isActive && userCompleted && (
            <span className="text-xs text-teal-600 dark:text-teal-400 font-medium flex items-center gap-1">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
              </svg>
              Done
            </span>
          )}
          {onDelete && task.status === 'locked' && (
            <button
              onClick={() => onDelete(task._id)}
              className="rounded-lg p-1.5 text-slate-400 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-900/20 transition-colors"
              title="Delete task"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
