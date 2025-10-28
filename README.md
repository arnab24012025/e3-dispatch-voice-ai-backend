# Dispatch Voice AI - Backend

AI Voice Agent Platform for Logistics Dispatch - FastAPI Backend

## 🚀 Tech Stack

- **Framework:** FastAPI
- **Language:** Python 3.10
- **Database:** PostgreSQL (via Supabase)
- **ORM:** SQLAlchemy
- **Authentication:** JWT (Bearer Token)
- **Voice AI:** Retell AI
- **Package Manager:** pip

## 📋 Prerequisites

- Python 3.10 or higher
- Supabase account (PostgreSQL database)
- Retell AI account and API key
- Groq API key (required)
- OpenAI API key (optional, for fallback)
- ngrok account (for local development webhooks)

## 🔧 Required External Services Setup

### 1. Supabase (Database)
1. Go to [https://supabase.com](https://supabase.com) and create account
2. Create new project
3. Go to **Settings → Database** and copy connection string
4. Go to **Settings → API** and copy Project URL and anon key

### 2. Retell AI (Voice Platform)
1. Sign up at [https://retellai.com](https://retellai.com)
2. Go to **Dashboard → API Keys** and copy your API key

### 3. Groq (LLM Provider - Required)
1. Sign up at [https://console.groq.com](https://console.groq.com)
2. Go to **API Keys** and create new key

### 4. OpenAI (LLM Provider - Optional)
1. Sign up at [https://platform.openai.com](https://platform.openai.com)
2. Go to **API Keys** and create new key

### 5. ngrok (Local Development)
1. Sign up at [https://ngrok.com](https://ngrok.com)
2. Download: `brew install ngrok` or from website
3. Get auth token from dashboard
4. Configure: `ngrok config add-authtoken <your-token>`

## 🛠️ Setup Instructions

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd dispatch-voice-ai-backend
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your actual values:

```env
# Database (Get from Supabase Dashboard)
DATABASE_URL=postgresql://user:password@db.supabase.co:5432/postgres
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key

# JWT (Generate with: openssl rand -hex 32)
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Retell AI
RETELL_API_KEY=your-retell-api-key
RETELL_AGENT_ID=your-retell-agent-id
RETELL_PHONE_NUMBER= for telephony calls - need to purchase

# Application
ENVIRONMENT=development
DEBUG=True
API_PREFIX=/api/v1

# CORS (Frontend URLs)
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

WEBHOOK_BASE_URL=your-ngrok-tunnel-url

GROQ_API_KEY=gsk_grok_api_key
GROQ_MODEL=llama-3.3-70b-versatile

OPENAI_API_KEY=sk-openai-key
OPENAI_MODEL=gpt-4o-mini

DEFAULT_LLM_PROVIDER=groq  
```

### 5. Initialize Database

The database tables will be created automatically on first run, but you can also run:

```bash
python -c "from app.database import init_db; init_db()"
```

### 6. Run the Application

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: `http://localhost:8000`

- **API Documentation:** http://localhost:8000/docs
- **Alternative Docs:** http://localhost:8000/redoc

## 📁 Project Structure

```
dispatch-voice-ai-backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Configuration management
│   ├── database.py          # Database connection
│   ├── models/              # SQLAlchemy models
│   │   ├── user.py
│   │   ├── agent.py
│   │   └── call.py
│   ├── schemas/             # Pydantic schemas
│   │   ├── auth.py
│   │   ├── agent.py
│   │   └── call.py
│   ├── routes/              # API endpoints
│   │   ├── auth.py
│   │   ├── agent.py
│   │   ├── call.py
│   │   └── webhook.py
│   ├── services/            # Business logic
│   │   ├── auth_service.py
│   │   ├── retell_service.py
│   │   └── transcript_processor.py
│   └── utils/               # Utilities
│       ├── jwt_handler.py
│       └── dependencies.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## 🔑 API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new admin user
- `POST /api/v1/auth/login` - Login and get JWT token
- `GET /api/v1/auth/me` - Get current user info

### Agent Configuration
- `POST /api/v1/agents` - Create agent configuration
- `GET /api/v1/agents` - List all agents
- `GET /api/v1/agents/{id}` - Get specific agent
- `PUT /api/v1/agents/{id}` - Update agent
- `DELETE /api/v1/agents/{id}` - Delete agent

### Calls
- `POST /api/v1/calls` - Initiate a call
- `GET /api/v1/calls` - List all calls
- `GET /api/v1/calls/{id}` - Get specific call
- `GET /api/v1/calls/{id}/refresh` - Refresh call status

### Webhooks
- `POST /api/v1/webhook/retell` - Retell AI webhook endpoint
- `POST /api/v1/webhook/retell/llm` - LLM WebSocket endpoint

## 🔐 Authentication

All protected endpoints require a JWT Bearer token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

### Getting a Token

1. Register a user:
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "username": "admin",
    "password": "securepassword"
  }'
```

2. Login to get token:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "securepassword"
  }'
```

## 🧪 Testing

You can test the API using:
- **Interactive Docs:** http://localhost:8000/docs (Swagger UI)
- **Postman/Insomnia:** Import the API endpoints
- **curl:** Command-line testing

## 🏗️ Database Models

### User
- Admin authentication
- JWT token management

### AgentConfiguration
- Agent prompts and system instructions
- Voice settings (backchanneling, fillers, interruption sensitivity)
- Retell AI agent ID mapping

### Call
- Call records with driver info
- Raw transcripts
- Structured results (extracted data)
- Call status tracking

## 📦 Key Features

✅ JWT-based authentication
✅ RESTful API design
✅ Async/await support
✅ Automatic API documentation
✅ CORS configured for frontend
✅ SQLAlchemy ORM (no raw SQL)
✅ Modular architecture
✅ Real-time webhook handling
✅ Transcript post-processing
✅ Dual LLM provider support (Groq + OpenAI with auto-fallback)
✅ Real-time WebSocket for Custom LLM integration
✅ Function calling for structured data extraction
✅ Post-call sentiment analysis and quality scoring
✅ Dashboard analytics and reporting

## 🎯 Core Capabilities

### Real-Time LLM Integration
- Custom WebSocket endpoint for Retell AI
- Dual LLM provider support (Groq + OpenAI) with auto-fallback
- Function calling for structured data extraction during calls
- Real-time conversation history tracking

### Post-Call Intelligence
- Automated sentiment analysis
- Quality scoring (1-10 scale)
- Key topic extraction
- Goal achievement detection
- Cooperation level assessment

### Call Management
- Phone call initiation via Retell AI
- Web call support for browser testing
- Call status tracking (initiated → completed)
- Recording URL storage
- Duration tracking

## 🔧 Development

### Adding New Dependencies

```bash
pip install <package-name>
pip freeze > requirements.txt
```

### Database Migrations (Future)

For production, consider using Alembic for database migrations:

```bash
alembic init alembic
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

## 🚨 Troubleshooting

### Database Connection Issues
- Verify Supabase credentials in `.env`
- Ensure database URL format is correct
- Check if IP is allowed in Supabase dashboard

### Import Errors
- Ensure virtual environment is activated
- Run `pip install -r requirements.txt` again

### Port Already in Use
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9
```

