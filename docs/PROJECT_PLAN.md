# Project Plan: Profu - Solo MVP (2 Months)

## Executive Summary

This document outlines the development plan for building the Profu MVP as a **solo developer** in **2 months** (8 weeks) with **5-7 hours/week** available time. The focus is on **math problems only** with **2 core features**: Progressive Hints and Theory Bot.

**Total Available Time**: ~40-56 hours  
**Developer Profile**: Data Scientist/AI Engineer (Python expert, weak on frontend)

---

## Project Phases (8 Weeks)

### Week 1: Setup & Content Collection
**Duration**: 1 week  
**Time**: 5-7 hours

#### Tasks:
1. **Project Setup** (2 hours)
   - Initialize FastAPI project
   - Set up React project (or React Native if mobile)
   - Git repository setup
   - Basic folder structure

2. **Content Collection** (3-5 hours)
   - Manually collect 20-30 math problems from past exams
   - Save as text files or images
   - Create simple JSON structure for problems
   - Extract barem for each problem (manual or GPT-4 help)

**Deliverables**:
- Project structure ready
- 20-30 math problems collected
- Basic problem data structure

---

### Week 2: Backend Foundation
**Duration**: 1 week  
**Time**: 5-7 hours

#### Tasks:
1. **Database Setup** (1-2 hours)
   - Set up PostgreSQL (Supabase free tier or Neon)
   - Create schema: users, problems, barem, hints
   - Simple migrations

2. **FastAPI Backend** (3-4 hours)
   - Basic FastAPI app structure
   - Authentication endpoints (register, login, JWT)
   - Problem CRUD endpoints
   - Barem retrieval endpoint
   - Deploy to Railway/Render (free tier)

3. **Basic Testing** (1 hour)
   - Test endpoints with Postman/curl
   - Verify database connections

**Deliverables**:
- Working FastAPI backend
- Database with schema
- Basic auth working
- Deployed backend URL

---

### Week 3: OCR & Problem Analysis
**Duration**: 1 week  
**Time**: 5-7 hours

#### Tasks:
1. **OCR Integration** (2-3 hours)
   - Integrate Tesseract OCR (Python)
   - Image preprocessing (PIL/OpenCV)
   - Text extraction from problem images
   - Test with sample images

2. **Problem Analysis** (2-3 hours)
   - GPT-4 API integration
   - Problem type classification
   - Topic extraction
   - Store analysis in database

3. **API Endpoint** (1 hour)
   - `/api/problems/scan` endpoint
   - Accept image, return problem text + analysis

**Deliverables**:
- OCR working (can scan problems)
- Problem analysis working
- Scan endpoint functional

---

### Week 4: Progressive Hints System
**Duration**: 1 week  
**Time**: 5-7 hours

#### Tasks:
1. **Hint Generation Logic** (3-4 hours)
   - GPT-4 prompt engineering for hints
   - Multi-level hint system (3-4 levels)
   - Store hints in database
   - Cache hints (avoid regenerating)

2. **API Endpoint** (1-2 hours)
   - `/api/problems/{id}/hints` endpoint
   - Progressive reveal (level 1, 2, 3, 4)
   - Track which hints user viewed

3. **Testing** (1 hour)
   - Test hint generation quality
   - Verify progressive reveal works

**Deliverables**:
- Hint generation working
- Progressive reveal working
- API endpoint ready

---

### Week 5: Theory Bot
**Duration**: 1 week  
**Time**: 5-7 hours

#### Tasks:
1. **Knowledge Base Setup** (2 hours)
   - Collect curriculum documents (text)
   - Create simple vector embeddings (Sentence Transformers)
   - Store in database or simple file

2. **RAG Implementation** (2-3 hours)
   - Question embedding
   - Retrieve relevant context
   - GPT-4 with context
   - Return answer with sources

3. **Chat API** (1-2 hours)
   - `/api/chat` endpoint
   - Conversation history (simple, in-memory or DB)
   - Romanian language support

**Deliverables**:
- Theory Bot working
- RAG implementation
- Chat endpoint ready

---

### Week 6: Frontend (Web App)
**Duration**: 1 week  
**Time**: 5-7 hours

#### Tasks:
1. **Basic React Setup** (1 hour)
   - Create React app (Vite or CRA)
   - Set up routing (React Router)
   - Basic layout components

2. **Core Pages** (3-4 hours)
   - Login/Register page (simple forms)
   - Dashboard (list of features)
   - Hints page (camera/upload, display hints)
   - Theory Bot page (chat interface)
   - Use Tailwind CSS + shadcn/ui components

3. **API Integration** (1-2 hours)
   - Axios/fetch setup
   - Connect to backend
   - Error handling
   - Loading states

**Deliverables**:
- Basic React app
- 2 main pages (Hints + Theory Bot)
- Connected to backend

---

### Week 7: Integration & Testing
**Duration**: 1 week  
**Time**: 5-7 hours

#### Tasks:
1. **End-to-End Testing** (2-3 hours)
   - Test full flow: scan → hints
   - Test Theory Bot chat
   - Fix integration bugs
   - Handle edge cases

2. **UI Polish** (2 hours)
   - Improve styling (use templates)
   - Add loading indicators
   - Error messages
   - Basic responsive design

3. **Deployment** (1-2 hours)
   - Deploy frontend (Vercel/Netlify)
   - Configure environment variables
   - Test deployed version
   - Fix CORS issues if any

**Deliverables**:
- Fully integrated app
- Deployed frontend
- Basic testing complete

---

### Week 8: Polish & Launch Prep
**Duration**: 1 week  
**Time**: 5-7 hours

#### Tasks:
1. **Bug Fixes** (2 hours)
   - Fix critical bugs
   - Improve error handling
   - Add basic validation

2. **Documentation** (1 hour)
   - README with setup instructions
   - API documentation (FastAPI auto-docs)
   - Basic user guide

3. **Final Testing** (1-2 hours)
   - Test on different devices/browsers
   - Verify all features work
   - Performance check

4. **Launch Prep** (1 hour)
   - Prepare for beta users
   - Set up basic analytics (optional)
   - Create simple landing page (optional)

**Deliverables**:
- Production-ready MVP
- Documentation
- Ready for beta users

---

## Total Effort Breakdown

| Week | Focus | Hours | Deliverable |
|-----|-------|-------|-------------|
| 1 | Setup & Content | 5-7 | 20-30 problems collected |
| 2 | Backend Foundation | 5-7 | FastAPI backend deployed |
| 3 | OCR & Analysis | 5-7 | Scan endpoint working |
| 4 | Progressive Hints | 5-7 | Hints feature complete |
| 5 | Theory Bot | 5-7 | Chat feature complete |
| 6 | Frontend | 5-7 | React app with 2 pages |
| 7 | Integration | 5-7 | Full app integrated |
| 8 | Polish | 5-7 | Production-ready MVP |
| **TOTAL** | **8 weeks** | **40-56 hours** | **Soft MVP** |

---

## Critical Path & Dependencies

### Critical Path:
1. **Week 1**: Content collection (blocks everything)
2. **Week 2**: Backend foundation (blocks all features)
3. **Week 3**: OCR (blocks hints feature)
4. **Week 4**: Hints (core feature)
5. **Week 5**: Theory Bot (core feature)
6. **Week 6**: Frontend (user interface)
7. **Week 7**: Integration (make it work)
8. **Week 8**: Polish (make it presentable)

### Dependencies:
- Week 3 depends on Week 2 (backend)
- Week 4 depends on Week 3 (OCR)
- Week 6 depends on Week 2 (backend API)
- Week 7 depends on Week 4, 5, 6 (all features)

---

## Resource Requirements

### Solo Developer
- **You**: Data Scientist/AI Engineer
- **Time**: 5-7 hours/week
- **Skills**: Python (expert), AI/ML (expert), Cloud (good), Frontend (basic)

### Infrastructure Costs (Monthly)
- **Backend Hosting**: Railway/Render free tier or $5-10/month
- **Database**: Supabase free tier or Neon free tier
- **Frontend Hosting**: Vercel/Netlify free tier
- **AI API (GPT-4)**: $20-50/month (depends on usage)
- **Storage**: Cloudinary free tier
- **Total**: ~$25-60/month

---

## Risk Mitigation for Main Blocker

### Blocker: Content Collection & Barem Matching

#### Solo Mitigation Strategy:

**1. Content Collection (Week 1)**
- **Approach**: Manual collection + GPT-4 help
- **Process**:
  1. Find 20-30 past exam problems (PDFs, images, websites)
  2. Use GPT-4 Vision API to extract text from images
  3. Manually verify and clean
  4. Store in simple JSON format
- **Time**: 3-5 hours
- **Tools**: GPT-4 Vision API, manual editing

**2. Problem Parsing**
- **Approach**: GPT-4 does the heavy lifting
- **Process**:
  1. Send problem image/text to GPT-4
  2. Ask GPT-4 to extract: problem text, topic, difficulty
  3. Store structured data
- **Time**: 1-2 hours (mostly automated)

**3. Barem Matching**
- **Approach**: GPT-4 + Manual verification
- **Process**:
  1. Send problem + barem document to GPT-4
  2. Ask GPT-4 to match problem to barem
  3. Manually verify matches (you're the expert)
  4. Store matches in database
- **Time**: 1-2 hours
- **Accuracy**: 80-90% with GPT-4, 100% after manual check

**Total Time for Blocker**: 5-9 hours (1 week)

---

## MVP Scope (Minimal Features)

### Included (Must Have):
1. ✅ **Progressive Hints**
   - Scan problem (image upload)
   - Get 3-4 progressive hints
   - Basic UI

2. ✅ **Theory Bot**
   - Chat interface
   - Ask curriculum questions
   - Get answers with sources

3. ✅ **Basic Auth**
   - Register/Login
   - JWT tokens
   - Simple user profiles

### Excluded (Post-MVP):
- ❌ Similar problems finder
- ❌ Exam simulator
- ❌ Advanced analytics
- ❌ Mobile app (web first)
- ❌ Offline mode
- ❌ Multiple subjects

---

## Success Criteria

### Development (Week 8):
- ✅ Backend API deployed and working
- ✅ Frontend deployed and accessible
- ✅ 2 core features functional
- ✅ Basic authentication working
- ✅ 20-30 problems in database

### Product (Post-Launch):
- 10-20 beta users can use the app
- Hints feature works end-to-end
- Theory Bot answers questions
- No critical bugs
- Basic feedback collection

---

## Recommendations

### Time Management:
1. **Focus on Backend First** (your strength)
2. **Use Templates for Frontend** (save time)
3. **Let GPT-4 Help** (code generation, parsing)
4. **Deploy Early** (Week 2-3, get something live)
5. **Iterate After MVP** (add features post-launch)

### Technology Choices:
1. **FastAPI** (Python, your strength)
2. **React** (easier than React Native for MVP)
3. **Tailwind + shadcn/ui** (copy-paste components)
4. **Managed Services** (save time on DevOps)
5. **GPT-4 API** (don't build custom models)

### Scope Management:
1. **2 Features Max** (Hints + Theory Bot)
2. **20-30 Problems** (enough to test)
3. **Web First** (easier than mobile)
4. **Simple UI** (functional, not beautiful)
5. **Deploy Early** (get feedback)

---

## Post-MVP Roadmap

### Month 3-4:
- Add Similar Problems feature
- Improve UI/UX
- Add more problems (50-100)
- Mobile app (if web works)

### Month 5-6:
- Add Exam Simulator
- Advanced analytics
- User feedback system
- Performance optimization

### Month 7+:
- Physics subject
- Computer Science subject
- Advanced features

---

## Conclusion

This **2-month solo MVP** is ambitious but achievable with:
- **Focused scope** (2 features, math only)
- **Your strengths** (Python, AI/ML, backend)
- **Simple frontend** (web app, templates)
- **Managed services** (save time)
- **GPT-4 assistance** (parsing, code generation)

**Key Success Factors**:
1. Start with content collection (Week 1)
2. Build backend first (your strength)
3. Keep frontend simple (templates)
4. Deploy early (Week 2-3)
5. Iterate after MVP launch

---

**Document Version**: 2.0 (Solo MVP)  
**Last Updated**: January 25, 2026  
**Developer**: Solo (Data Scientist/AI Engineer)
