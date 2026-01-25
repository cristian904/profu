# Requirements Document: Profu - Solo MVP (2 Months)

## 1. Project Overview

### 1.1 Purpose
This document defines the functional and non-functional requirements for "Profu" **Soft MVP** - a web application designed to replace expensive private tutoring for Romanian high school seniors preparing for the Bacalaureat exam.

**This is a solo development effort** targeting a **2-month MVP** with **5-7 hours/week** available time.

### 1.2 Scope
- **MVP Focus**: Mathematics only
- **Target Platform**: Web application (React) - mobile later
- **Target Users**: Romanian high school seniors (12th grade students)
- **Development**: Solo developer (Data Scientist/AI Engineer)

### 1.3 Problem Statement
- Private tutoring costs 400-600 RON/month per subject
- School system inadequately prepares students for Bacalaureat
- Physical tutoring requires travel time and scheduling constraints
- Limited accessibility for students in rural areas or with financial constraints

### 1.4 Solution Overview
An AI-driven web application that replicates the private tutoring experience at a fraction of the cost, accessible 24/7 from any location.

---

## 2. Stakeholders

- **Primary Users**: High school seniors preparing for Bacalaureat
- **Developer**: Solo (Data Scientist/AI Engineer)
- **Future**: Parents/guardians, educational institutions

---

## 3. Functional Requirements (MVP Scope)

### 3.1 FR-001: Progressive Hints System (MVP - Priority 1)
**Priority**: High (Must Have)  
**Description**: Students can upload a math problem image and receive progressive hints, similar to asking a tutor for guidance.

**Requirements**:
- FR-001.1: Image upload (file input) - no camera API needed for MVP
- FR-001.2: OCR capability to extract problem text from image
- FR-001.3: AI analysis of problem to identify type and topic
- FR-001.4: Multi-level hint system (3-4 progressive hints per problem)
- FR-001.5: Hints should guide without giving direct answers
- FR-001.6: Progressive reveal (user clicks to see next hint level)

**MVP Simplifications**:
- ❌ No camera API (use file upload)
- ❌ No handwritten support initially (printed text only)
- ❌ No analytics tracking (add later)
- ✅ Basic OCR (Tesseract)
- ✅ GPT-4 for hint generation

**Acceptance Criteria**:
- User can upload a problem image
- OCR extracts text (accuracy > 80% for printed text)
- Hints are contextually relevant and progressively revealing
- System responds within 5 seconds

---

### 3.2 FR-002: Theory Bot (MVP - Priority 1)
**Priority**: High (Must Have)  
**Description**: AI-powered chatbot that answers theoretical questions using curriculum content.

**Requirements**:
- FR-002.1: Natural language chat interface
- FR-002.2: Knowledge base integration (curriculum documents)
- FR-002.3: Context-aware responses based on curriculum
- FR-002.4: Support for Romanian language
- FR-002.5: Conversation history (basic, in-memory or database)
- FR-002.6: Ability to ask follow-up questions

**MVP Simplifications**:
- ❌ No internet search (curriculum only)
- ❌ No source citations initially (add later)
- ❌ No LaTeX rendering initially (plain text)
- ✅ Simple RAG (Retrieval-Augmented Generation)
- ✅ GPT-4 with context

**Acceptance Criteria**:
- Response time < 5 seconds
- Answers are accurate and curriculum-aligned
- Conversation context maintained
- Supports Romanian language

---

### 3.3 FR-003: User Authentication (MVP - Required)
**Priority**: Medium (Required for MVP)  
**Description**: Basic user accounts to track progress.

**Requirements**:
- FR-003.1: User registration (email, password)
- FR-003.2: User login/logout
- FR-003.3: JWT token authentication
- FR-003.4: Basic user profile (name, email)

**MVP Simplifications**:
- ❌ No social login (email/password only)
- ❌ No password reset (add later)
- ❌ No email verification (add later)
- ✅ Basic JWT auth

**Acceptance Criteria**:
- Users can register and login
- Sessions persist
- Protected routes work

---

### 3.4 FR-004: Similar Problems Finder (Post-MVP)
**Priority**: Low (Excluded from MVP)  
**Status**: Deferred to post-MVP

---

### 3.5 FR-005: Exam Simulator (Post-MVP)
**Priority**: Low (Excluded from MVP)  
**Status**: Deferred to post-MVP

---

## 4. Non-Functional Requirements (MVP)

### 4.1 Performance
- NFR-001: App loads in < 3 seconds
- NFR-002: OCR processing < 10 seconds (acceptable for MVP)
- NFR-003: AI response time < 5 seconds
- NFR-004: Basic error handling (no crashes)

### 4.2 Usability
- NFR-005: Simple, functional UI (not beautiful, but usable)
- NFR-006: Romanian language interface
- NFR-007: Basic responsive design (works on mobile browsers)

### 4.3 Security & Privacy
- NFR-008: HTTPS (automatic with hosting)
- NFR-009: Secure authentication (JWT)
- NFR-010: Basic input validation
- NFR-011: Environment variables for secrets

### 4.4 Reliability
- NFR-012: Basic error handling
- NFR-013: Graceful degradation (show errors to user)
- NFR-014: No data loss (database backups)

### 4.5 Scalability
- NFR-015: Support 10-50 concurrent users (MVP scale)
- NFR-016: Cloud-based infrastructure (managed services)

### 4.6 Compatibility
- NFR-017: Works on modern browsers (Chrome, Firefox, Safari)
- NFR-018: Responsive design (mobile-friendly web app)

---

## 5. Technical Requirements (MVP)

### 5.1 Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL (Supabase/Neon free tier) or SQLite for MVP
- **Authentication**: JWT tokens
- **OCR**: Tesseract (pytesseract)
- **AI/ML**: GPT-4 API
- **Hosting**: Railway/Render (free tier)

### 5.2 Frontend
- **Framework**: React (Vite)
- **Styling**: Tailwind CSS
- **Components**: shadcn/ui (copy-paste)
- **State Management**: React hooks (no Redux)
- **Hosting**: Vercel/Netlify (free tier)

### 5.3 Infrastructure
- **Cloud Provider**: AWS/GCP (free tier where possible)
- **No Docker**: Use managed services
- **No CI/CD**: Manual deployment is OK for MVP

---

## 6. Data Requirements (MVP)

### 6.1 Problem Database
- **Minimum**: 20-30 math problems from past exams
- **Format**: Text + images
- **Metadata**: Year, topic, difficulty (basic)
- **Barem**: Matched to problems (manual or GPT-4 assisted)

### 6.2 Content Sources
- Past exam problems (publicly available)
- Curriculum documents (text format)
- Basic knowledge base for Theory Bot

### 6.3 User Data
- Profile information (email, name)
- Chat history (Theory Bot)
- Hints viewed (optional, add later)

---

## 7. Constraints & Assumptions

### 7.1 Constraints
- Solo developer (5-7 hours/week)
- 2-month timeline
- Limited frontend expertise
- Math problems only
- Web app (not native mobile)

### 7.2 Assumptions
- Students have internet access
- Students can upload images
- GPT-4 API available and affordable
- Managed services free tiers sufficient
- 20-30 problems enough for MVP testing

---

## 8. MVP Exclusions (Post-MVP)

### Features NOT in MVP:
- ❌ Similar Problems Finder
- ❌ Exam Simulator
- ❌ Advanced analytics
- ❌ Parent dashboard
- ❌ Social features
- ❌ Mobile app (web first)
- ❌ Offline mode
- ❌ Multiple subjects (math only)
- ❌ Handwritten OCR
- ❌ LaTeX rendering
- ❌ Source citations
- ❌ Password reset
- ❌ Email verification

### Features for Post-MVP:
- Similar Problems (Week 9-10)
- Exam Simulator (Week 11-12)
- Mobile app (Month 3)
- Advanced features (Month 4+)

---

## 9. Success Criteria (MVP)

### Development (Week 8):
- ✅ Backend API deployed and working
- ✅ Frontend deployed and accessible
- ✅ 2 core features functional (Hints + Theory Bot)
- ✅ Basic authentication working
- ✅ 20-30 problems in database

### Product (Post-Launch):
- 10-20 beta users can use the app
- Hints feature works end-to-end
- Theory Bot answers questions
- No critical bugs
- Basic feedback collection

---

## 10. Future Enhancements (Post-MVP)

### Month 3-4:
- Similar Problems Finder
- Exam Simulator (basic)
- Improved UI/UX
- More problems (50-100)
- Mobile app

### Month 5-6:
- Advanced analytics
- User progress tracking
- Better OCR (handwritten support)
- LaTeX rendering
- Source citations

### Month 7+:
- Physics subject
- Computer Science subject
- Advanced features
- Custom ML models

---

## 11. Dependencies

- Access to past Bacalaureat exam problems (20-30)
- GPT-4 API access
- Cloud infrastructure (free tiers)
- Curriculum documents (for Theory Bot)

---

## 12. Glossary

- **Bacalaureat (Bac)**: Romanian national high school graduation exam
- **Barem**: Official grading rubric/scoring guide for exam problems
- **OCR**: Optical Character Recognition
- **MVP**: Minimum Viable Product
- **RAG**: Retrieval-Augmented Generation
- **RON**: Romanian Leu (currency)

---

**Document Version**: 2.0 (Solo MVP)  
**Last Updated**: January 25, 2026  
**Developer**: Solo (Data Scientist/AI Engineer)
