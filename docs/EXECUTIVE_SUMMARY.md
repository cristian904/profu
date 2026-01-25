# Executive Summary: Profu Mobile App (Solo MVP)

## Project Overview

**Profu** is an AI-powered mobile application designed to replace expensive private tutoring for Romanian high school seniors preparing for the Bacalaureat exam. The app replicates the private tutoring experience at a fraction of the cost (target: <50 RON/month vs. 400-600 RON/month for physical tutors).

**This is a solo development effort** by a data scientist/AI engineer with strong Python and cloud expertise, targeting a **soft MVP in 2 months** focusing on **math problems only**.

---

## Key Features (Soft MVP - 2 Months)

**Priority 1 (Must Have)**:
1. **Progressive Hints** - Scan problems, get step-by-step hints (basic version)
2. **Theory Bot** - AI chatbot for curriculum questions (basic version)

**Priority 2 (Nice to Have - if time permits)**:
3. **Similar Problems Finder** - Find practice problems (simplified)
4. **Exam Simulator** - Basic practice exams (minimal version)

---

## Timeline & Constraints

### Timeline
- **Soft MVP Launch**: 2 months (8 weeks)
- **Available Time**: 5-7 hours/week
- **Total Effort**: ~40-56 hours (~1-1.4 person-weeks)

### Developer Profile
- **Role**: Solo developer (Data Scientist/AI Engineer)
- **Strengths**: Python, AI/ML, Cloud, Backend
- **Weaknesses**: Frontend development (will "vibe code" it)
- **Focus**: Math problems only

### Budget Estimate
- **Development**: $0 (solo effort)
- **Infrastructure**: $50-200/month (cloud hosting, AI APIs)
- **Total First 2 Months**: ~$100-400

---

## Development Phases (8 Weeks)

| Week | Focus | Key Deliverable |
|------|-------|----------------|
| **Week 1** | Setup & Content | Project setup, collect 20-30 math problems |
| **Week 2** | Backend Foundation | FastAPI backend, database, basic auth |
| **Week 3** | OCR & Problem Analysis | OCR pipeline, problem parsing |
| **Week 4** | Hint Generation | AI-powered hint system |
| **Week 5** | Theory Bot | Basic chat interface with RAG |
| **Week 6** | Frontend (Web First) | Simple React web app |
| **Week 7** | Integration & Testing | Connect frontend to backend, test |
| **Week 8** | Polish & Deploy | Final touches, deploy to cloud |

**Total**: 8 weeks (~40-56 hours of work)

---

## Critical Blocker: Content Collection & Barem Matching

### The Challenge
- Collecting past exam problems from various sources
- Parsing problems from PDFs/images
- Matching problems to their "barem" (grading rubrics)

### Solo Mitigation Strategy
1. **Start Small**: Collect 20-30 problems manually (not 100+)
2. **Use GPT-4**: Let AI help with parsing and matching
3. **Manual Verification**: Review matches yourself (you're the domain expert)
4. **Iterate**: Add more problems after MVP launch

### Estimated Effort
- Content Collection: 2-3 hours (20-30 problems)
- Parsing: 1-2 hours (use GPT-4 Vision API)
- Barem Matching: 1-2 hours (GPT-4 + manual check)
- **Total**: ~4-7 hours (1 week of work)

---

## Technology Stack (Solo-Optimized)

### Backend (Your Strength)
- **Framework**: FastAPI (Python) - fast, async, auto-docs
- **Database**: PostgreSQL (managed: Supabase or Neon) or SQLite for MVP
- **AI/ML**: 
  - GPT-4 API (hints, theory bot)
  - Tesseract OCR (Python wrapper)
  - Sentence Transformers (similarity)
- **Cloud**: AWS/GCP (use free tier where possible)

### Frontend (Simple Approach)
- **Option A**: React web app (easier than mobile for MVP)
- **Option B**: React Native (if you want mobile from start)
- **UI Library**: Tailwind CSS + shadcn/ui (copy-paste components)
- **State**: Simple React hooks (no Redux needed)

### Infrastructure
- **Hosting**: Vercel/Netlify (frontend), Railway/Render (backend)
- **Database**: Supabase (free tier) or Neon (PostgreSQL)
- **Storage**: Cloudinary (free tier) for images
- **No Docker/K8s**: Use managed services to save time

---

## MVP Scope (Minimal Features)

### Included
- ✅ Basic user authentication (email/password)
- ✅ Progressive hints (3-4 levels, GPT-4 powered)
- ✅ Theory Bot (basic chat, RAG with curriculum)
- ✅ Simple web interface (or basic mobile)
- ✅ 20-30 math problems with barem

### Excluded (Post-MVP)
- ❌ Similar problems finder (add later)
- ❌ Exam simulator (add later)
- ❌ Advanced analytics
- ❌ Mobile app (web first, mobile later)
- ❌ Multiple subjects (math only for MVP)
- ❌ Offline mode
- ❌ Social features

---

## Success Metrics (Soft MVP)

### Development
- ✅ Working backend API
- ✅ Basic frontend interface
- ✅ 2 core features functional (Hints + Theory Bot)
- ✅ Deployed and accessible

### Product (Post-Launch)
- 10-20 beta users
- Basic feedback collection
- Core features work end-to-end
- No critical bugs

---

## Top Risks (Solo Developer)

1. **Time Constraints** (Critical) - Only 5-7 hours/week
   - **Mitigation**: Focus on 2 features max, use templates/copy-paste
   
2. **Frontend Complexity** (High) - Not your strength
   - **Mitigation**: Use web app (easier), copy UI components, keep it simple
   
3. **Content Collection** (Medium) - Need problems quickly
   - **Mitigation**: Start with 20-30 problems, use GPT-4 to help parse
   
4. **Scope Creep** (High) - Temptation to add features
   - **Mitigation**: Strict MVP scope, add features post-launch

---

## Recommendations

### Immediate Actions (Week 1)
1. ✅ Set up project structure (FastAPI + React)
2. ✅ Collect 20-30 math problems manually
3. ✅ Set up cloud accounts (AWS/GCP free tier)
4. ✅ Get GPT-4 API key

### Development Strategy
1. **Backend First**: Build API endpoints (your strength)
2. **Simple Frontend**: Use templates, copy-paste components
3. **Use AI**: Let GPT-4 help with code generation
4. **Deploy Early**: Get something working and deployed ASAP
5. **Iterate**: Add features after MVP is live

### Success Factors
- Keep scope minimal (2 features max)
- Use managed services (save time)
- Focus on backend (your strength)
- Simple frontend (functional, not beautiful)
- Deploy early and iterate

---

## Next Steps

1. **Week 1**: Project setup + collect 20-30 problems
2. **Week 2**: FastAPI backend + database
3. **Week 3-4**: OCR + Hint generation
4. **Week 5**: Theory Bot
5. **Week 6**: Simple React frontend
6. **Week 7**: Integration
7. **Week 8**: Deploy and polish

---

## Questions to Address

1. **Frontend Choice**: Web app (easier) or mobile (harder)?
2. **Content**: Do you have access to past exam problems?
3. **Deployment**: Which cloud provider do you prefer?
4. **Features**: Which 2 features are most important for MVP?

---

**Document Version**: 2.0 (Solo MVP)  
**Date**: January 25, 2026  
**Developer**: Solo (Data Scientist/AI Engineer)

---

## Quick Reference

- **Full Requirements**: See `REQUIREMENTS.md`
- **Detailed Plan**: See `PROJECT_PLAN.md`
- **Technical Details**: See `TECHNICAL_ARCHITECTURE.md`
- **Workload Breakdown**: See `WORKLOAD_BREAKDOWN.md`
- **Risk Analysis**: See `RISK_REGISTER.md`
