# TeamFlow — Collaborative Task Management

A modern full-stack web application for collaborative task management with strict sequential task progression.

## Features

- **JWT Authentication** — Secure signup/login with role-based access (Leader / Member)
- **Team System** — Create teams, generate invite codes, and invite members
- **Sequential Task Workflow** — Tasks unlock only when ALL members complete the current one
- **Real-time Updates** — Socket.io powered live progress syncing
- **Leader Dashboard** — Create tasks, view member progress, and track overall completion
- **Dark Mode** — System-aware theme toggle
- **Mobile Responsive** — Clean, professional design

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite + Tailwind CSS |
| Backend | Node.js + Express |
| Database | MongoDB + Mongoose |
| Auth | JWT (JSON Web Tokens) |
| Real-time | Socket.io |

## Project Structure

```
teamflow/
├── backend/
│   ├── config/
│   │   └── db.js              # MongoDB connection
│   ├── middleware/
│   │   └── auth.js            # JWT protect middleware
│   ├── models/
│   │   ├── User.js
│   │   ├── Team.js
│   │   └── Task.js
│   ├── routes/
│   │   ├── auth.js            # /api/auth (register, login)
│   │   ├── teams.js           # /api/teams (create, join, me)
│   │   └── tasks.js           # /api/tasks (CRUD + complete)
│   ├── server.js              # Express + Socket.io server
│   ├── package.json
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── context/
    │   │   ├── AuthContext.jsx # Auth state management
    │   │   └── ThemeContext.jsx# Dark mode
    │   ├── components/
    │   │   ├── Navbar.jsx
    │   │   ├── ProtectedRoute.jsx
    │   │   ├── TaskCard.jsx
    │   │   ├── MemberList.jsx
    │   │   ├── ProgressBar.jsx
    │   │   └── CreateTaskModal.jsx
    │   ├── pages/
    │   │   ├── Login.jsx
    │   │   ├── Register.jsx
    │   │   ├── TeamSetup.jsx
    │   │   └── Dashboard.jsx
    │   ├── App.jsx
    │   ├── main.jsx
    │   └── index.css
    ├── index.html
    ├── vite.config.js
    ├── tailwind.config.js
    └── package.json
```

## Setup Instructions

### Prerequisites

- [Node.js](https://nodejs.org) v18 or higher
- [MongoDB](https://www.mongodb.com) running locally (or use MongoDB Atlas)

### 1. Backend Setup

```bash
cd teamflow/backend

# Install dependencies
npm install

# Create environment file
cp .env.example .env
```

Edit `.env` and set your values:

```env
PORT=5000
MONGO_URI=mongodb://localhost:27017/teamflow
JWT_SECRET=your_very_secure_secret_here
CLIENT_URL=http://localhost:5173
```

Start the backend:

```bash
# Development (with auto-reload)
npm run dev

# Production
npm start
```

### 2. Frontend Setup

```bash
cd teamflow/frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The app will be available at **http://localhost:5173**

### 3. Running both together

Open two terminal windows:

```bash
# Terminal 1 — Backend
cd teamflow/backend && npm run dev

# Terminal 2 — Frontend
cd teamflow/frontend && npm run dev
```

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register a new user |
| POST | `/api/auth/login` | Login and receive JWT |

### Teams
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/teams` | Create a new team (user becomes leader) |
| POST | `/api/teams/join` | Join a team via invite code |
| GET | `/api/teams/me` | Get current user's team |
| DELETE | `/api/teams/leave` | Leave the team |

### Tasks
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/tasks` | Create a task (leader only) |
| GET | `/api/tasks` | Get all tasks for team |
| PATCH | `/api/tasks/:id/complete` | Mark task as completed |
| DELETE | `/api/tasks/:id` | Delete a task (leader only) |

## Task Progression Rules

1. The **first task** is immediately **active** when created
2. Subsequent tasks are **locked** by default
3. Each team member can mark the active task as **complete**
4. When **ALL members** complete the current task:
   - The current task status changes to `completed`
   - The next task automatically becomes `active`
5. Only **locked** tasks can be deleted by the leader

## Socket.io Events

| Event | Direction | Payload |
|-------|-----------|---------|
| `join:team` | Client → Server | `teamId` |
| `task:created` | Server → Client | Task object |
| `task:updated` | Server → Client | Updated task object |
| `task:unlocked` | Server → Client | Newly active task object |
| `task:deleted` | Server → Client | `{ taskId }` |
