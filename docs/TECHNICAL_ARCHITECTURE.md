# Technical Architecture: Profu Solo MVP

## 1. System Overview

### 1.1 Architecture Pattern
**Simple Monolithic Architecture** - FastAPI backend + React frontend. No microservices, no complex infrastructure.

```
┌─────────────┐
│ React Web   │ (Frontend)
│   App       │
└──────┬──────┘
       │ HTTPS/REST API
       ▼
┌─────────────────┐
│  FastAPI Backend │ (Python)
│  (Single Service)│
└────────┬────────┘
         │
    ┌────┴────┬──────────────┐
    ▼         ▼              ▼
┌────────┐ ┌──────────┐ ┌──────────┐
│PostgreSQL│ │ GPT-4   │ │  Cloud   │
│ Database│ │   API    │ │ Storage  │
└────────┘ └──────────┘ └──────────┘
```

**Why Simple?**
- Solo developer
- 2-month timeline
- Focus on features, not infrastructure
- Easy to deploy and maintain

---

## 2. Frontend (React Web App)

### 2.1 Technology Stack
**React** (not React Native for MVP - easier to develop)

- **Framework**: React 18+ with Vite (faster than CRA)
- **Language**: TypeScript (optional, JavaScript is fine)
- **Styling**: Tailwind CSS (utility-first, fast)
- **Components**: shadcn/ui (copy-paste components)
- **State Management**: React hooks (useState, useContext) - no Redux needed
- **Routing**: React Router v6
- **HTTP Client**: Axios or fetch API
- **Forms**: React Hook Form (simple validation)

### 2.2 Project Structure
```
frontend/
├── src/
│   ├── pages/
│   │   ├── Login.tsx
│   │   ├── Register.tsx
│   │   ├── Dashboard.tsx
│   │   ├── Hints.tsx          # Progressive hints page
│   │   └── TheoryBot.tsx      # Chat interface
│   ├── components/
│   │   ├── Button.tsx
│   │   ├── Input.tsx
│   │   ├── ChatMessage.tsx
│   │   └── HintCard.tsx
│   ├── services/
│   │   └── api.ts             # API client
│   ├── hooks/
│   │   └── useAuth.ts         # Auth hook
│   ├── utils/
│   │   └── constants.ts
│   └── App.tsx
├── public/
└── package.json
```

### 2.3 Key Features Implementation

**Camera/Image Upload**:
- Use HTML5 `<input type="file">` (simpler than camera API)
- Image preview before upload
- Upload to backend, backend does OCR

**Chat Interface**:
- Simple message list
- Input field at bottom
- Loading states
- Basic message bubbles

**Hints Display**:
- Show problem text
- Button to reveal next hint
- Progressive reveal (level 1, 2, 3, 4)

---

## 3. Backend (FastAPI)

### 3.1 Technology Stack
**Python FastAPI** (your strength)

- **Framework**: FastAPI 0.100+
- **Language**: Python 3.10+
- **Database ORM**: SQLAlchemy (or Tortoise ORM)
- **Authentication**: JWT (python-jose)
- **Validation**: Pydantic models
- **OCR**: pytesseract (Tesseract wrapper)
- **Image Processing**: PIL/Pillow, OpenCV (optional)
- **AI/ML**: 
  - OpenAI GPT-4 API
  - sentence-transformers (for similarity, if needed)
- **File Upload**: python-multipart

### 3.2 Project Structure
```
backend/
├── app/
│   ├── main.py                # FastAPI app
│   ├── models/
│   │   ├── user.py
│   │   ├── problem.py
│   │   └── barem.py
│   ├── schemas/
│   │   ├── user.py
│   │   ├── problem.py
│   │   └── hint.py
│   ├── api/
│   │   ├── auth.py
│   │   ├── problems.py
│   │   ├── hints.py
│   │   └── chat.py
│   ├── services/
│   │   ├── ocr.py
│   │   ├── ai.py              # GPT-4 integration
│   │   └── hints.py
│   ├── database.py
│   └── config.py
├── requirements.txt
└── .env
```

### 3.3 API Endpoints

```python
# Authentication
POST   /api/auth/register
POST   /api/auth/login
POST   /api/auth/refresh

# Problems
GET    /api/problems
GET    /api/problems/{id}
POST   /api/problems/scan        # Upload image, OCR + analysis
POST   /api/problems             # Create problem manually

# Hints
POST   /api/problems/{id}/hints  # Get hints (progressive)
GET    /api/problems/{id}/hints/{level}  # Get specific hint level

# Theory Bot
POST   /api/chat                  # Send message
GET    /api/chat/history         # Get conversation history

# Health
GET    /health
```

### 3.4 Key Services

**OCR Service** (`services/ocr.py`):
```python
def extract_text_from_image(image_file):
    # Use pytesseract
    # Preprocess image (contrast, rotation)
    # Return text
```

**AI Service** (`services/ai.py`):
```python
def generate_hints(problem_text, level):
    # Call GPT-4 API
    # Return hint for specific level
    
def answer_question(question, context):
    # RAG: Retrieve context
    # Call GPT-4 with context
    # Return answer
```

---

## 4. Database

### 4.1 PostgreSQL (Recommended)
**Use managed service**: Supabase (free tier) or Neon (free tier)

**Schema** (simplified):
```sql
-- Users
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    password_hash VARCHAR NOT NULL,
    name VARCHAR,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Problems
CREATE TABLE problems (
    id SERIAL PRIMARY KEY,
    content_text TEXT NOT NULL,
    content_image_url VARCHAR,
    topic VARCHAR,
    difficulty VARCHAR,
    year INTEGER,
    points INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Barem
CREATE TABLE barem (
    id SERIAL PRIMARY KEY,
    problem_id INTEGER REFERENCES problems(id),
    grading_criteria TEXT,
    points_distribution JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Hints (cached)
CREATE TABLE hints (
    id SERIAL PRIMARY KEY,
    problem_id INTEGER REFERENCES problems(id),
    level INTEGER,
    hint_text TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Chat History
CREATE TABLE chat_messages (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    message TEXT,
    response TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 4.2 Alternative: SQLite (For MVP)
If you want even simpler setup:
- Use SQLite for development
- Migrate to PostgreSQL later
- No database hosting needed initially

---

## 5. AI/ML Components

### 5.1 OCR Pipeline
```python
# Simple OCR flow
image → PIL preprocessing → pytesseract → text → GPT-4 cleanup
```

**Libraries**:
- `pytesseract` (Tesseract OCR wrapper)
- `Pillow` (image processing)
- `opencv-python` (optional, for advanced preprocessing)

### 5.2 Hint Generation
```python
# GPT-4 API call
prompt = f"""
You are a math tutor. Given this problem:
{problem_text}

Provide a hint for level {level} (1-4):
- Level 1: General direction
- Level 2: Specific concept
- Level 3: Step-by-step guidance
- Level 4: Almost complete solution

Hint:
"""
```

### 5.3 Theory Bot (RAG)
```python
# Simple RAG implementation
1. User question → embed with sentence-transformers
2. Search curriculum documents (simple text search or vector search)
3. Retrieve top 3 relevant chunks
4. Send to GPT-4: question + context
5. Return answer
```

**Knowledge Base**:
- Store curriculum text in database or files
- Use sentence-transformers for embeddings (optional, can use simple text search)
- Vector search with pgvector (optional, can use PostgreSQL full-text search)

---

## 6. Infrastructure (Minimal)

### 6.1 Hosting Options

**Backend**:
- **Railway** (recommended): Easy deployment, free tier
- **Render**: Free tier, easy setup
- **Fly.io**: Free tier, good for Python
- **AWS Lambda**: Serverless (more complex)

**Frontend**:
- **Vercel** (recommended): Free, automatic deployments
- **Netlify**: Free, easy setup
- **GitHub Pages**: Free, static hosting

**Database**:
- **Supabase**: Free tier PostgreSQL
- **Neon**: Free tier PostgreSQL
- **Railway**: PostgreSQL addon

### 6.2 No Complex Infrastructure
- ❌ No Docker (use managed services)
- ❌ No Kubernetes
- ❌ No API Gateway (FastAPI handles routing)
- ❌ No separate services (monolith is fine)
- ❌ No CI/CD initially (manual deploy is OK)

### 6.3 Environment Variables
```bash
# Backend .env
DATABASE_URL=postgresql://...
OPENAI_API_KEY=sk-...
JWT_SECRET=your-secret-key
CORS_ORIGINS=http://localhost:3000,https://your-frontend.vercel.app

# Frontend .env
VITE_API_URL=https://your-backend.railway.app
```

---

## 7. Security (Basic)

### 7.1 Authentication
- JWT tokens (access + refresh)
- Password hashing (bcrypt)
- Simple rate limiting (optional)

### 7.2 API Security
- CORS configuration
- Input validation (Pydantic)
- SQL injection prevention (SQLAlchemy ORM)

### 7.3 Data Protection
- HTTPS (automatic with hosting)
- Environment variables for secrets
- Basic GDPR compliance (user data deletion)

---

## 8. Development Workflow

### 8.1 Local Setup
```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

### 8.2 Deployment
```bash
# Backend (Railway)
railway login
railway init
railway up

# Frontend (Vercel)
vercel login
vercel deploy
```

---

## 9. Technology Decisions Summary

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Backend | FastAPI (Python) | Your strength, fast development |
| Frontend | React (Web) | Easier than mobile, large ecosystem |
| Database | PostgreSQL (Supabase) | Free tier, managed |
| AI/ML | GPT-4 API | Best quality, no model training |
| OCR | Tesseract (pytesseract) | Free, good enough for MVP |
| Styling | Tailwind CSS | Fast styling, utility-first |
| Components | shadcn/ui | Copy-paste, beautiful |
| Hosting | Railway + Vercel | Free tiers, easy deployment |

---

## 10. Code Examples

### 10.1 FastAPI Endpoint (Hints)
```python
from fastapi import APIRouter, Depends
from app.services.ai import generate_hint
from app.services.ocr import extract_text

router = APIRouter()

@router.post("/problems/scan")
async def scan_problem(image: UploadFile):
    # OCR
    text = extract_text(image)
    
    # Analyze with GPT-4
    analysis = await analyze_problem(text)
    
    return {"text": text, "analysis": analysis}

@router.post("/problems/{problem_id}/hints")
async def get_hint(problem_id: int, level: int):
    # Check cache
    hint = get_cached_hint(problem_id, level)
    if hint:
        return hint
    
    # Generate with GPT-4
    problem = get_problem(problem_id)
    hint = await generate_hint(problem.text, level)
    
    # Cache
    cache_hint(problem_id, level, hint)
    
    return {"level": level, "hint": hint}
```

### 10.2 React Component (Hints Page)
```tsx
import { useState } from 'react';
import { uploadImage, getHints } from '../services/api';

function HintsPage() {
  const [problemText, setProblemText] = useState('');
  const [hints, setHints] = useState([]);
  const [currentLevel, setCurrentLevel] = useState(0);

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    const result = await uploadImage(file);
    setProblemText(result.text);
  };

  const revealHint = async () => {
    const hint = await getHints(problemId, currentLevel + 1);
    setHints([...hints, hint]);
    setCurrentLevel(currentLevel + 1);
  };

  return (
    <div>
      <input type="file" onChange={handleUpload} />
      <div>{problemText}</div>
      {hints.map((hint, i) => (
        <div key={i}>Level {i+1}: {hint.text}</div>
      ))}
      <button onClick={revealHint}>Get Next Hint</button>
    </div>
  );
}
```

---

## 11. MVP Simplifications

### What We're NOT Building:
- ❌ Microservices architecture
- ❌ Complex infrastructure
- ❌ Mobile app (web first)
- ❌ Advanced analytics
- ❌ Real-time features
- ❌ Offline mode
- ❌ Complex state management
- ❌ Custom ML models (use GPT-4)

### What We ARE Building:
- ✅ Simple FastAPI backend
- ✅ React web app
- ✅ 2 core features (Hints + Theory Bot)
- ✅ Basic authentication
- ✅ Managed services (save time)
- ✅ Simple, functional UI

---

## 12. Post-MVP Enhancements

### Easy Wins:
- Add Similar Problems (use sentence-transformers)
- Improve UI/UX
- Add more problems
- Mobile app (React Native)

### Medium Effort:
- Exam Simulator
- Advanced analytics
- Better OCR (custom model)
- Offline mode

### Future:
- Multiple subjects
- Advanced features
- Custom ML models
- Scale infrastructure

---

**Document Version**: 2.0 (Solo MVP)  
**Last Updated**: January 25, 2026  
**Developer**: Solo (Data Scientist/AI Engineer)
