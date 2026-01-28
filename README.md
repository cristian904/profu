# Profu - AI-Powered Bacalaureat Tutor App (Solo MVP)

![Backend Tests](https://github.com/YOUR_USERNAME/profu/actions/workflows/backend-tests.yml/badge.svg)
![Frontend Tests](https://github.com/YOUR_USERNAME/profu/actions/workflows/frontend-tests.yml/badge.svg)
![CI Pipeline](https://github.com/YOUR_USERNAME/profu/actions/workflows/ci.yml/badge.svg)

## 📚 Documentation

- **[Implemented Features](docs/IMPLEMENTED_FEATURES.md)** - Business-level overview of all completed features
- **[Technical Architecture](docs/TECHNICAL_ARCHITECTURE.md)** - System design and technical details
- **[Project Plan](docs/PROJECT_PLAN.md)** - Development roadmap and timeline
- **[Requirements](docs/REQUIREMENTS.md)** - Product requirements and specifications

## Quick Start Guide

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Install dependencies:
```bash
poetry install
```

3. Create `.env` file and add your Google Gemini API key:
```bash
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
```

Get your API key from: https://makersuite.google.com/app/apikey

4. Run the backend server:
```bash
poetry run uvicorn profu_backend.main:app --reload
```

The backend will be available at `http://localhost:8000`

### Local Supabase (optional, for CRUD data)

To run Supabase locally with Docker for users, conversations, exam problems, etc.:

1. From the repo root: `npm install` then `npx supabase start`.
2. Open Supabase Studio at the URL shown (e.g. `http://127.0.0.1:54323`).
3. In the Flutter app, set the Supabase URL and anon key in `flutter_app/lib/main.dart` (from the `npx supabase start` output).

See [supabase/README.md](supabase/README.md) for details.

### Frontend Setup

1. Navigate to Flutter app directory:
```bash
cd flutter_app
```

2. Install dependencies:
```bash
flutter pub get
```

3. Run the Flutter app:
```bash
flutter run
```

For web:
```bash
flutter run -d chrome
```

### Current Features

- **N-am înțeles la clasă**: Interactive chat interface with:
  - **Streaming AI responses** powered by Gemini 2.0 Flash
  - **Conversation memory** for contextual follow-up questions
  - **Markdown formatting** (bold, italic, headings, lists, code blocks)
  - **LaTeX math rendering** for formulas (inline: `$x^2$`, display: `$$\frac{a}{b}$$`)
  - **Interactive function graphs** for mathematical visualizations
  - **Dark theme** UI for comfortable viewing
- **Burger menu navigation** for easy access to features
- **Real-time token streaming** from backend to frontend using SSE
- **Configurable AI prompts** via YAML files (no code changes needed)
- **Comprehensive test coverage** for both backend and frontend

### Testing

#### Backend Tests
```bash
cd backend
poetry install --with dev
poetry run pytest
```

Tests include:
- API endpoint validation
- Pydantic model validation
- Streaming functionality
- Error handling
- LLM configuration

#### Frontend Tests
```bash
cd flutter_app
flutter test
```

Tests include:
- Widget rendering
- Navigation flow
- User interactions
- Message handling
- UI components

### CI/CD Pipeline

The project includes automated GitHub Actions workflows:
- **Backend Tests**: Runs on every push/PR affecting backend code
- **Frontend Tests**: Runs on every push/PR affecting frontend code
- **Combined CI**: Runs both test suites in parallel

See [CI/CD Documentation](.github/CI_CD.md) for detailed setup and configuration.

**Features:**
- ✅ Automated testing on push/PR
- ✅ Code coverage reporting (Codecov)
- ✅ Parallel test execution
- ✅ Dependency caching for fast builds
- ✅ Branch protection ready

---

## Project Documentation

This repository contains the complete requirements engineering and project planning documentation for the **Profu** web application - an AI-driven tutoring app for Romanian high school seniors preparing for the Bacalaureat exam.

**This is a solo development effort** targeting a **2-month MVP** with **5-7 hours/week** available time, focusing on **math problems only**.

---

## 📚 Documentation Structure

### 1. [EXECUTIVE_SUMMARY.md](./EXECUTIVE_SUMMARY.md)
**Start here!** Quick overview of the project, timeline, budget, and key decisions.
- Project overview
- Timeline & budget summary
- Critical blockers
- Success metrics
- Next steps

### 2. [REQUIREMENTS.md](./REQUIREMENTS.md)
Complete functional and non-functional requirements specification.
- Problem statement & solution
- Functional requirements (all 4 core features)
- Non-functional requirements (performance, security, etc.)
- Technical requirements
- Success criteria

### 3. [PROJECT_PLAN.md](./PROJECT_PLAN.md)
Detailed development plan with phases, tasks, and timelines.
- 6 development phases (52 weeks total)
- Task breakdown by phase
- Critical path analysis
- Resource requirements
- **Main blocker mitigation strategy** (Content & Barem Matching)

### 4. [WORKLOAD_BREAKDOWN.md](./WORKLOAD_BREAKDOWN.md)
Detailed workload estimation by role and phase.
- Effort by role (Backend, Mobile, ML, QA, etc.)
- Resource allocation
- Cost estimation
- Parallelization opportunities

### 5. [TECHNICAL_ARCHITECTURE.md](./TECHNICAL_ARCHITECTURE.md)
Technical architecture and technology decisions.
- System architecture
- Technology stack
- Database design
- AI/ML components
- API design
- Infrastructure

### 6. [RISK_REGISTER.md](./RISK_REGISTER.md)
Comprehensive risk analysis and mitigation strategies.
- 10 identified risks
- Probability & impact assessment
- Mitigation strategies
- Contingency plans
- **Focus on main blocker**: Content Collection & Barem Matching

---

## 🎯 Quick Facts

| Metric | Value |
|--------|-------|
| **Timeline** | 2 months (8 weeks) |
| **Team Size** | 1 person (solo) |
| **Available Time** | 5-7 hours/week |
| **Total Effort** | ~40-56 hours |
| **Budget** | $100-400 (2 months) |
| **Target Users** | Romanian high school seniors |
| **MVP Focus** | Mathematics only (web app) |

---

## 🚀 Core Features (MVP)

**Priority 1 (Must Have)**:
1. **Progressive Hints** - Upload problem images, get step-by-step hints
2. **Theory Bot** - AI chatbot for curriculum questions

**Priority 2 (Post-MVP)**:
3. **Similar Problems Finder** - Find practice problems (deferred)
4. **Exam Simulator** - Practice exams (deferred)

---

## ⚠️ Critical Constraints (Solo MVP)

### Time Constraints (5-7 hours/week)

**Challenge**: Limited time available per week. Must be very focused.

**Mitigation Strategy**:
- Strict scope (2 features max)
- Use templates and copy-paste components
- Managed services (save time)
- GPT-4 assistance for code generation
- Simple architecture (no microservices)

**See**: [PROJECT_PLAN.md](./PROJECT_PLAN.md) - 8-week timeline  
**See**: [RISK_REGISTER.md](./RISK_REGISTER.md) - RISK-001

### Content Collection

**Challenge**: Need 20-30 math problems quickly.

**Mitigation Strategy**:
- Start small (20-30 problems, not 100+)
- Use GPT-4 Vision API for parsing
- Manual verification (you're the expert)
- ~5-7 hours in Week 1

---

## 📋 Development Phases (8 Weeks)

```
Week 1: Setup & Content (5-7h)
    ↓
Week 2: Backend Foundation (5-7h)
    ↓
Week 3: OCR & Analysis (5-7h)
    ↓
Week 4: Progressive Hints (5-7h)
    ↓
Week 5: Theory Bot (5-7h)
    ↓
Week 6: Frontend (5-7h)
    ↓
Week 7: Integration (5-7h)
    ↓
Week 8: Polish & Deploy (5-7h)
```

**Total**: 8 weeks (~40-56 hours)

---

## 👤 Developer Profile

### Solo Developer
- **Role**: Data Scientist/AI Engineer
- **Strengths**: Python, AI/ML, Cloud, Backend
- **Weaknesses**: Frontend development
- **Time**: 5-7 hours/week
- **Focus**: Math problems only

---

## 💰 Budget Breakdown (2 Months)

### Development Costs
- Solo developer: $0 (your time)

### Infrastructure (Monthly)
- Backend hosting: $0-10 (Railway/Render free tier)
- Database: $0 (Supabase/Neon free tier)
- Frontend hosting: $0 (Vercel/Netlify free tier)
- AI API (GPT-4): $20-50 (depends on usage)
- Storage: $0 (Cloudinary free tier)
- **Total**: ~$20-60/month

### 2-Month Total
- **Infrastructure**: ~$40-120
- **Total**: ~$40-120 (very affordable!)

---

## 🛠️ Technology Stack (Solo-Optimized)

### Frontend
- **Framework**: React (Web app, not mobile for MVP)
- **Styling**: Tailwind CSS
- **Components**: shadcn/ui (copy-paste)
- **State**: React hooks (no Redux)

### Backend
- **Framework**: FastAPI (Python - your strength)
- **Database**: PostgreSQL (Supabase/Neon free tier)
- **OCR**: Tesseract (pytesseract)
- **AI/ML**: GPT-4 API

### Infrastructure
- **Backend Hosting**: Railway/Render (free tier)
- **Frontend Hosting**: Vercel/Netlify (free tier)
- **Database**: Supabase/Neon (free tier)
- **No Docker/K8s**: Use managed services

---

## 📊 Success Metrics (MVP)

### Development (Week 8)
- ✅ Backend API deployed and working
- ✅ Frontend deployed and accessible
- ✅ 2 core features functional (Hints + Theory Bot)
- ✅ Basic authentication working
- ✅ 20-30 problems in database

### Product (Post-Launch)
- 10-20 beta users can use the app
- Hints feature works end-to-end
- Theory Bot answers questions
- No critical bugs
- Basic feedback collection

---

## 🎯 MVP Scope (Minimal)

### Included (Must Have)
- ✅ Basic user authentication (email/password)
- ✅ Progressive hints (3-4 levels, GPT-4 powered)
- ✅ Theory Bot (basic chat, RAG with curriculum)
- ✅ Simple web interface
- ✅ 20-30 math problems with barem

### Excluded (Post-MVP)
- ❌ Similar problems finder
- ❌ Exam simulator
- ❌ Advanced analytics
- ❌ Mobile app (web first)
- ❌ Multiple subjects (math only)
- ❌ Offline mode

---

## 📅 Recommended Reading Order

1. **Start**: [EXECUTIVE_SUMMARY.md](./EXECUTIVE_SUMMARY.md) - Get the big picture
2. **Understand Requirements**: [REQUIREMENTS.md](./REQUIREMENTS.md) - What we're building
3. **Review Plan**: [PROJECT_PLAN.md](./PROJECT_PLAN.md) - How we'll build it
4. **Check Workload**: [WORKLOAD_BREAKDOWN.md](./WORKLOAD_BREAKDOWN.md) - Who does what
5. **Technical Details**: [TECHNICAL_ARCHITECTURE.md](./TECHNICAL_ARCHITECTURE.md) - How it works
6. **Risk Management**: [RISK_REGISTER.md](./RISK_REGISTER.md) - What could go wrong

---

## 🚨 Top Risks (Solo Developer)

1. **Time Constraints** (Critical) - Only 5-7h/week, strict scope needed
2. **Frontend Complexity** (High) - Not your strength, use templates
3. **Scope Creep** (High) - Temptation to add features, stay focused
4. **Content Collection** (Medium) - Need 20-30 problems quickly
5. **Burnout** (Medium) - 2 months of side project work

---

## ✅ Next Steps

1. **Week 1**: Project setup + collect 20-30 math problems
2. **Week 2**: FastAPI backend + database setup
3. **Week 3**: OCR integration + problem analysis
4. **Week 4**: Progressive hints feature
5. **Week 5**: Theory Bot feature
6. **Week 6**: React frontend
7. **Week 7**: Integration & testing
8. **Week 8**: Polish & deploy

---

## 📝 Document Status

| Document | Version | Last Updated | Status |
|----------|---------|--------------|--------|
| EXECUTIVE_SUMMARY | 2.0 (Solo MVP) | Jan 25, 2026 | ✅ Complete |
| REQUIREMENTS | 2.0 (Solo MVP) | Jan 25, 2026 | ✅ Complete |
| PROJECT_PLAN | 2.0 (Solo MVP) | Jan 25, 2026 | ✅ Complete |
| WORKLOAD_BREAKDOWN | 2.0 (Solo MVP) | Jan 25, 2026 | ✅ Complete |
| TECHNICAL_ARCHITECTURE | 2.0 (Solo MVP) | Jan 25, 2026 | ✅ Complete |
| RISK_REGISTER | 2.0 (Solo MVP) | Jan 25, 2026 | ✅ Complete |

---

## 🤝 Contributing

This is a requirements and planning document. For development:
1. Create development branches from this documentation
2. Update documentation as requirements evolve
3. Track changes in version control

---

## 📞 Contact & Questions

For questions about:
- **Requirements**: See REQUIREMENTS.md
- **Timeline**: See PROJECT_PLAN.md
- **Technical**: See TECHNICAL_ARCHITECTURE.md
- **Risks**: See RISK_REGISTER.md

---

## 📄 License

This documentation is for internal project planning purposes.

---

**Last Updated**: January 25, 2026  
**Project Status**: Planning Phase (Solo MVP)  
**Next Milestone**: Week 1 - Setup & Content Collection  
**Developer**: Solo (Data Scientist/AI Engineer)
