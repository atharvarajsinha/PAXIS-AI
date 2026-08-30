# PAXIS AI — Technical TERMS

## Tech Stack

### Frontend

* React
* Vite
* React Router
* JavaScript
* CSS

### Backend

* Python
* Django
* Django REST Framework

### AI

* Google Gemini
* `google-genai` Python SDK
* Groq Python SDK as fallback
* Serper for study-material search

### Database

* PostgreSQL
* Django ORM

### Authentication

* Django Authentication
* DRF Token Authentication

### Configuration

* Environment variables using `python-dotenv`

---

## System Architecture

```text
┌─────────────────────┐
│    React Frontend   │
│      Port: 5173     │
└──────────┬──────────┘
           │
           │ REST API / SSE
           ▼
┌─────────────────────┐
│   Django Backend    │
│      Port: 8000     │
└───────┬─────┬───────┘
        │     │
        │     ├──────────────► Google Gemini
        │     │                    │
        │     │                    │ Failure
        │     │                    ▼
        │     │                  Groq
        │     │
        │     ├──────────────► Serper
        │     │
        ▼     ▼
┌─────────────────────┐
│     PostgreSQL      │
└─────────────────────┘
```

The frontend communicates only with Django. AI API keys and database credentials remain on the backend.

---

# Project Structure

```text
PAXIS-AI/
│
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── venv/
│   │
│   ├── config/
│   │   └── Django project configuration
│   │
│   ├── accounts/
│   │   └── Authentication, users and profiles
│   │
│   ├── chat/
│   │   └── Chat API, AI services and conversations
│   │
│   └── progress/
│       └── Plans, steps, milestones and dashboard
│
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── components/
│   │   ├── context/
│   │   ├── pages/
│   │   └── services/
│   │
│   └── public/
│
├── .env.example
└── .env
```

---

# Prerequisites

Install:

* Python 3.x
* Node.js
* npm
* PostgreSQL
* Git

You also need API credentials for:

* Google Gemini
* Groq
* Serper

---

# Environment Configuration

Create the environment file from the template:

```bash
cp .env.example .env
```

For Windows:

```powershell
copy .env.example .env
```

Configure the root `backend/.env`:

```dotenv
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.5-flash-lite

GROQ_API_KEY=
GROQ_MODEL=

SERPER_API_KEY=

DB_NAME=ai_learning_path
DB_USER=
DB_PASSWORD=
DB_HOST=localhost
DB_PORT=5432

DJANGO_SECRET_KEY=
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

`GEMINI_MODEL` must be set to a model available to your Gemini account. PostgreSQL credentials must also be configured.

**Never commit `.env` or real API keys to Git.**

---

# PostgreSQL Setup

Create the database:

```sql
CREATE DATABASE ai_learning_path;
```

Configure the database credentials in `.env`:

```dotenv
DB_NAME=ai_learning_path
DB_USER=your_postgres_username
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432
```

---

# Backend Setup

From the repository root:

### 1. Create virtual environment

```bash
python -m venv backend/venv
```

### 2. Activate virtual environment

#### Windows

```powershell
backend\venv\Scripts\activate
```

#### Linux/macOS

```bash
source backend/venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r backend/requirements.txt
```

### 4. Run Django checks

```bash
cd backend
python manage.py check
```

### 5. Run database migrations

```bash
python manage.py migrate
```

### 6. Start Django server

```bash
python manage.py runserver
```

Backend:

```text
http://localhost:8000
```

The test suite can be executed with:

```bash
python manage.py test
```

---

# Frontend Setup

Open a **new terminal**.

### 1. Navigate to frontend

```bash
cd frontend
```

### 2. Install dependencies

```bash
npm install
```

### 3. Start development server

```bash
npm run dev
```

Frontend:

```text
http://localhost:5173
```

If the backend is running at a different URL, configure:

```dotenv
VITE_API_BASE_URL=http://your-backend-url
```

---

# Running the Complete Application

You need **two terminals**.

### Terminal 1 — Backend

```bash
python -m venv backend/venv
backend\venv\Scripts\activate
pip install -r backend/requirements.txt

cd backend
python manage.py migrate
python manage.py runserver
```

### Terminal 2 — Frontend

```bash
cd frontend
npm install
npm run dev
```

Then open:

```text
http://localhost:5173
```

---

# Authentication

Authentication uses DRF token authentication.

After login/register, the frontend receives a token and sends it with API requests:

```http
Authorization: Token <token>
```

Register and login do not require authentication. Other API endpoints require a valid token.

---

# API Structure

## Authentication

| Method | Endpoint              | Purpose          |
| ------ | --------------------- | ---------------- |
| POST   | `/api/auth/register/` | Register user    |
| POST   | `/api/auth/login/`    | Login            |
| POST   | `/api/auth/logout/`   | Logout           |
| GET    | `/api/auth/me/`       | Get current user |
| POST   | `/api/auth/password/` | Change password  |

## Profile

| Method | Endpoint        | Purpose                  |
| ------ | --------------- | ------------------------ |
| GET    | `/api/profile/` | Get profile              |
| PUT    | `/api/profile/` | Update profile           |
| PATCH  | `/api/profile/` | Partially update profile |

## Chat

| Method | Endpoint                   | Purpose             |
| ------ | -------------------------- | ------------------- |
| POST   | `/api/chat/`               | Send AI message     |
| GET    | `/api/conversations/`      | List conversations  |
| GET    | `/api/conversations/<id>/` | Get conversation    |
| PATCH  | `/api/conversations/<id>/` | Rename conversation |
| DELETE | `/api/conversations/<id>/` | Delete conversation |

## Progress

| Method | Endpoint                | Purpose              |
| ------ | ----------------------- | -------------------- |
| GET    | `/api/dashboard/`       | Dashboard data       |
| GET    | `/api/plans/`           | List learning plans  |
| POST   | `/api/plans/`           | Create learning plan |
| GET    | `/api/plans/<id>/`      | Get learning plan    |
| PATCH  | `/api/plans/<id>/`      | Update/archive plan  |
| DELETE | `/api/plans/<id>/`      | Delete plan          |
| PATCH  | `/api/steps/<id>/`      | Update step          |
| PATCH  | `/api/milestones/<id>/` | Update milestone     |

---

# AI Request Flow

```text
User enters learning request
          │
          ▼
React Frontend
          │
          ▼
POST /api/chat/
          │
          ▼
Django Backend
          │
          ├── Load user profile
          │
          ├── Load conversation history
          │
          ▼
     Google Gemini
          │
          ├── Success ───────► Response
          │
          └── Temporary failure
                    │
                    ▼
                  Groq
                    │
                    ▼
                 Response
          │
          ▼
       Django
          │
          ├── Save conversation
          ├── Save roadmap
          └── Return response
          │
          ▼
       React
```

Gemini is the primary provider. Groq is automatically used when Gemini encounters temporary quota, rate-limit, server, or connection failures.

---

# Chat Streaming

The chat endpoint uses **Server-Sent Events (SSE)**.

Example:

```text
data: {"conversation_id":12}

data: {"status":"Generating your roadmap..."}

data: {"response":"..."}

data: {
  "roadmap": {
    "goal":"Python Developer",
    "duration":"6 months",
    "steps":[],
    "projects":[],
    "milestones":[],
    "next_action":"..."
  }
}

event: end
data: {}
```

---

# Study Material Pipeline

```text
Roadmap Topic
      │
      ▼
    Django
      │
      ▼
    Serper
      │
      ├── Web Results
      └── YouTube Results
              │
              ▼
          Gemini
              │
              ▼
     Selected Resources
              │
              ▼
        React Frontend
```

Serper is used by the backend to retrieve current web/video results, after which Gemini selects suitable resources.

---

# Development Commands

### Backend

```bash
cd backend

# Activate environment
backend\venv\Scripts\activate

# Check project
python manage.py check

# Apply migrations
python manage.py migrate

# Run server
python manage.py runserver

# Run tests
python manage.py test
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

---

# Local Development URLs

| Service    | URL                          |
| ---------- | ---------------------------- |
| Frontend   | `http://localhost:5173`      |
| Backend    | `http://localhost:8000`      |
| Django API | `http://localhost:8000/api/` |
| PostgreSQL | `localhost:5432`             |

---

# Important Configuration Rules

* Keep Gemini, Groq and Serper API keys in backend `.env`.
* Never expose AI API keys in React.
* Never commit `.env`.
* PostgreSQL runs on port `5432` by default.
* Django runs on port `8000`.
* Vite runs on port `5173`.
* Frontend communicates with AI providers only through Django.
* Authenticated API requests use DRF token authentication.

---

# Production Notes

Before production deployment:

```dotenv
DJANGO_DEBUG=False
```

Configure:

```dotenv
DJANGO_SECRET_KEY=<secure-secret>
DJANGO_ALLOWED_HOSTS=<your-domain>
CORS_ALLOWED_ORIGINS=<your-frontend-domain>
```

Use production PostgreSQL credentials and keep all API keys server-side.

---

# Current Technical Status

Implemented:

* React frontend
* Django REST backend
* PostgreSQL persistence
* Token authentication
* User profiles
* Conversation persistence
* Gemini integration
* Groq fallback
* Serper integration
* Streaming chat responses
* Learning-plan persistence
* Progress tracking
* Dashboard APIs
* Django test suite

A live Gemini request requires valid Gemini and PostgreSQL credentials.
