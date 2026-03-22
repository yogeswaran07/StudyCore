export default function MemberList({ members, leaderId, activeTask }) {
  const completedIds = new Set(
    (activeTask?.completedBy || []).map((u) => (u._id || u).toString())
  )

  return (
    <ul className="divide-y divide-slate-100 dark:divide-slate-800">
      {members.map((member) => {
        const id = (member._id || member).toString()
        const isLeader = leaderId?.toString() === id
        const completed = completedIds.has(id)

        return (
          <li key={id} className="flex items-center justify-between py-2.5">
            <div className="flex items-center gap-2.5">
              <div className="h-8 w-8 rounded-full bg-primary-100 dark:bg-primary-900/40 flex items-center justify-center text-primary-700 dark:text-primary-300 text-sm font-semibold">
                {(member.name || '?').charAt(0).toUpperCase()}
              </div>
              <div>
                <p className="text-sm font-medium text-slate-800 dark:text-slate-200 leading-tight">
                  {member.name || 'Unknown'}
                </p>
                <p className="text-xs text-slate-400 dark:text-slate-500">
                  {isLeader ? 'Leader' : 'Member'}
                </p>
              </div>
            </div>
            {activeTask && (
              <span
                className={completed ? 'text-teal-500' : 'text-slate-300 dark:text-slate-600'}
                title={completed ? 'Completed' : 'Pending'}
              >
                {completed ? (
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                )}
              </span>
            )}
          </li>
        )
      })}
    </ul>
  )
}
