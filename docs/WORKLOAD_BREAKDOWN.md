# Workload Breakdown: Profu Solo MVP (2 Months)

## Quick Reference Summary

| Week | Focus | Hours | Key Deliverable |
|------|-------|-------|-----------------|
| **Week 1** | Setup & Content | 5-7 | 20-30 problems collected |
| **Week 2** | Backend Foundation | 5-7 | FastAPI backend deployed |
| **Week 3** | OCR & Analysis | 5-7 | Scan endpoint working |
| **Week 4** | Progressive Hints | 5-7 | Hints feature complete |
| **Week 5** | Theory Bot | 5-7 | Chat feature complete |
| **Week 6** | Frontend | 5-7 | React app with 2 pages |
| **Week 7** | Integration | 5-7 | Full app integrated |
| **Week 8** | Polish | 5-7 | Production-ready MVP |
| **TOTAL** | **8 weeks** | **40-56 hours** | **Soft MVP** |

---

## Detailed Breakdown by Week

### Week 1: Setup & Content Collection
**Total Time**: 5-7 hours

| Task | Time | Description |
|------|------|-------------|
| Project setup | 1-2h | Git repo, folder structure, FastAPI + React init |
| Content collection | 3-5h | Find 20-30 math problems, extract text, get barem |
| **Total** | **5-7h** | **20-30 problems ready** |

**Deliverables**:
- Project structure
- 20-30 math problems in JSON/text format
- Basic data structure defined

---

### Week 2: Backend Foundation
**Total Time**: 5-7 hours

| Task | Time | Description |
|------|------|-------------|
| Database setup | 1-2h | Supabase/Neon setup, schema design, migrations |
| FastAPI structure | 2-3h | Main app, models, schemas, basic endpoints |
| Authentication | 1-2h | Register, login, JWT tokens |
| Deployment | 1h | Deploy to Railway/Render, test |
| **Total** | **5-7h** | **Backend API working** |

**Deliverables**:
- FastAPI backend running
- Database with schema
- Auth endpoints working
- Deployed backend URL

---

### Week 3: OCR & Problem Analysis
**Total Time**: 5-7 hours

| Task | Time | Description |
|------|------|-------------|
| OCR integration | 2-3h | Tesseract setup, image preprocessing, text extraction |
| Problem analysis | 2-3h | GPT-4 integration, classification, topic extraction |
| Scan endpoint | 1h | API endpoint for image upload + OCR + analysis |
| **Total** | **5-7h** | **Scan feature working** |

**Deliverables**:
- OCR working (can extract text from images)
- Problem analysis working
- `/api/problems/scan` endpoint functional

---

### Week 4: Progressive Hints System
**Total Time**: 5-7 hours

| Task | Time | Description |
|------|------|-------------|
| Hint generation logic | 3-4h | GPT-4 prompts, multi-level hints, caching |
| Hints API endpoint | 1-2h | `/api/problems/{id}/hints` with progressive reveal |
| Testing | 1h | Test hint quality, verify levels work |
| **Total** | **5-7h** | **Hints feature complete** |

**Deliverables**:
- Hint generation working
- Progressive reveal (levels 1-4)
- API endpoint ready

---

### Week 5: Theory Bot
**Total Time**: 5-7 hours

| Task | Time | Description |
|------|------|-------------|
| Knowledge base | 2h | Collect curriculum docs, create embeddings (optional) |
| RAG implementation | 2-3h | Question embedding, context retrieval, GPT-4 with context |
| Chat API | 1-2h | `/api/chat` endpoint, conversation history |
| **Total** | **5-7h** | **Theory Bot working** |

**Deliverables**:
- Theory Bot functional
- RAG working (or simple context retrieval)
- Chat endpoint ready

---

### Week 6: Frontend (React Web App)
**Total Time**: 5-7 hours

| Task | Time | Description |
|------|------|-------------|
| React setup | 1h | Vite/CRA, routing, basic layout |
| Auth pages | 1h | Login/Register forms (simple) |
| Hints page | 2h | Image upload, problem display, hints reveal |
| Theory Bot page | 1h | Chat interface, message display |
| API integration | 1h | Axios setup, connect to backend |
| **Total** | **5-7h** | **Frontend working** |

**Deliverables**:
- React app running
- 2 main pages (Hints + Theory Bot)
- Connected to backend

---

### Week 7: Integration & Testing
**Total Time**: 5-7 hours

| Task | Time | Description |
|------|------|-------------|
| End-to-end testing | 2-3h | Test full flows, fix bugs, edge cases |
| UI polish | 2h | Styling improvements, loading states, errors |
| Deployment | 1-2h | Deploy frontend (Vercel), configure env vars |
| **Total** | **5-7h** | **App integrated** |

**Deliverables**:
- Fully integrated app
- Deployed frontend
- Basic testing complete

---

### Week 8: Polish & Launch Prep
**Total Time**: 5-7 hours

| Task | Time | Description |
|------|------|-------------|
| Bug fixes | 2h | Fix critical bugs, improve error handling |
| Documentation | 1h | README, API docs, basic user guide |
| Final testing | 1-2h | Test on different devices, performance check |
| Launch prep | 1h | Prepare for beta users, basic analytics (optional) |
| **Total** | **5-7h** | **MVP ready** |

**Deliverables**:
- Production-ready MVP
- Documentation
- Ready for beta users

---

## Time Allocation by Category

### Backend Development: ~20-28 hours (50%)
- FastAPI setup: 2-3h
- Database: 2-3h
- Authentication: 2-3h
- OCR: 2-3h
- AI/ML integration: 5-7h
- API endpoints: 4-6h
- Testing: 2-3h
- Deployment: 2-3h

### Frontend Development: ~10-14 hours (25%)
- React setup: 1-2h
- Pages/components: 5-7h
- API integration: 2-3h
- Styling: 2-3h

### Content & Data: ~5-7 hours (12.5%)
- Problem collection: 3-5h
- Barem matching: 1-2h
- Knowledge base: 1-2h

### Integration & Polish: ~5-7 hours (12.5%)
- End-to-end testing: 2-3h
- Bug fixes: 2-3h
- Documentation: 1h

---

## Effort by Feature

| Feature | Time | Complexity |
|---------|------|------------|
| **Progressive Hints** | 8-10h | Medium |
| - OCR | 2-3h | Medium |
| - Hint generation | 3-4h | Easy (GPT-4) |
| - API + Frontend | 3-3h | Easy |
| **Theory Bot** | 5-7h | Medium |
| - RAG setup | 2-3h | Medium |
| - Chat API | 1-2h | Easy |
| - Frontend | 2-2h | Easy |
| **Authentication** | 2-3h | Easy |
| **Content Collection** | 5-7h | Easy (manual) |
| **Frontend Setup** | 5-7h | Easy |
| **Integration** | 5-7h | Easy |
| **Polish** | 5-7h | Easy |

---

## Risk-Adjusted Timeline

### Best Case (7 hours/week, no blockers)
- **Timeline**: 8 weeks
- **Total**: 56 hours
- **Buffer**: Can add polish, better UI

### Most Likely (6 hours/week, minor issues)
- **Timeline**: 8 weeks
- **Total**: 48 hours
- **Buffer**: Some features might be basic

### Worst Case (5 hours/week, major blockers)
- **Timeline**: 8-10 weeks
- **Total**: 40-50 hours
- **Mitigation**: Reduce scope, focus on 1 feature first

---

## Time-Saving Strategies

### 1. Use Templates & Copy-Paste
- **Frontend**: shadcn/ui components (copy-paste)
- **Backend**: FastAPI templates, copy structure
- **Save**: ~5-10 hours

### 2. Managed Services
- **Database**: Supabase (no setup)
- **Hosting**: Railway/Vercel (one-click deploy)
- **Save**: ~3-5 hours

### 3. GPT-4 Assistance
- **Code generation**: Ask GPT-4 for code snippets
- **Parsing**: Use GPT-4 Vision for problem extraction
- **Save**: ~3-5 hours

### 4. Simple Architecture
- **No microservices**: Monolith is fine
- **No Docker**: Use managed services
- **Save**: ~5-8 hours

### 5. Web First (Not Mobile)
- **React web**: Easier than React Native
- **Save**: ~5-10 hours

**Total Time Saved**: ~21-38 hours

---

## Weekly Time Breakdown

### Typical Week (6 hours)
- **Monday**: 1-2 hours (evening)
- **Wednesday**: 1-2 hours (evening)
- **Saturday**: 2-3 hours (weekend)
- **Sunday**: 1 hour (if needed)

### Focus Areas by Week
1. **Week 1**: Content (manual work, can do while watching TV)
2. **Week 2**: Backend (your strength, efficient)
3. **Week 3**: OCR (interesting, AI work)
4. **Week 4**: Hints (AI work, your strength)
5. **Week 5**: Theory Bot (AI work, your strength)
6. **Week 6**: Frontend (weaker area, use templates)
7. **Week 7**: Integration (testing, debugging)
8. **Week 8**: Polish (final touches)

---

## Recommendations

### Time Management:
1. **Block time**: Schedule 5-7 hours/week in calendar
2. **Focus sessions**: 1-2 hour focused work blocks
3. **Avoid context switching**: Finish one feature before starting another
4. **Use weekends**: 2-3 hours on Saturday/Sunday
5. **Deploy early**: Get something working Week 2-3

### Efficiency Tips:
1. **Backend first**: Your strength, faster progress
2. **Use AI**: GPT-4 for code generation, parsing
3. **Copy-paste**: Don't build from scratch
4. **Simple UI**: Functional, not beautiful
5. **Deploy often**: Test in production early

### Scope Management:
1. **2 features max**: Hints + Theory Bot
2. **20-30 problems**: Enough to test
3. **Web first**: Easier than mobile
4. **Basic auth**: Email/password is fine
5. **Iterate later**: Add features post-MVP

---

## Post-MVP Time Estimates

### Similar Problems Feature: 5-7 hours
- Vector embeddings: 2h
- Similarity search: 2h
- Frontend: 1-2h
- Integration: 1h

### Exam Simulator: 10-15 hours
- Exam generation: 3-4h
- Timer: 1-2h
- UI: 3-4h
- Barem display: 2-3h
- Integration: 1-2h

### Mobile App: 15-20 hours
- React Native setup: 2-3h
- Port components: 5-7h
- Native features: 3-4h
- Testing: 2-3h
- Deployment: 2-3h

---

**Document Version**: 2.0 (Solo MVP)  
**Last Updated**: January 25, 2026  
**Developer**: Solo (Data Scientist/AI Engineer)
