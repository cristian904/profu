# Profu - Implemented Features

**Last Updated:** April 6, 2026

This document provides a business-level overview of all features currently implemented in Profu. It serves as a living record of the application's capabilities and should be updated whenever new features are added or existing functionality changes significantly.

---

## 📱 Current Product Status

**Platform:** Flutter Mobile App + FastAPI Backend  
**Focus:** Math problems for Romanian Bacalaureat preparation  
**Stage:** Active Development (MVP Phase)

---

## ✅ Implemented Features

### 1. N-am înțeles la clasă (I Didn't Understand in Class)

**Status:** ✅ Fully Implemented  
**Implementation Date:** January 2026

A dual-mode AI tutoring system that helps students understand concepts they didn't grasp during classroom instruction. Students can choose between two learning approaches:

#### Mode 1: Clarify Once (Direct Answers)
- **What it does:** Provides immediate, comprehensive explanations to student questions
- **How it works:** 
  - Student asks a question about a concept they don't understand
  - AI responds with a complete, detailed explanation immediately
  - Supports follow-up questions for deeper clarification
  - All responses include mathematical formulas (LaTeX), markdown formatting, and visual graphs when relevant
  
- **Best for:** Students who need quick clarification or want direct answers to specific questions

- **Example Flow:**
  ```
  Student: "What is the Pythagorean theorem?"
  AI: [Provides complete explanation with formula, examples, and visual graph]
  Student: "Can you show me an example?"
  AI: [Provides detailed worked example]
  ```

#### Mode 2: Clarify Step-by-Step (Guided Learning)
- **What it does:** Uses Socratic method to guide students through understanding complex concepts
- **How it works:**
  - Student asks about a concept they want to understand
  - **Preview:** AI shows a roadmap of 2-3 prerequisite concepts that will be covered
  - **Progress Tracking:** Each concept shows progress (e.g., "[Concept 2/3] 📖")
  - AI asks questions about each prerequisite one by one
  - **Confidence Detection:** AI adjusts tone based on student certainty in answers
  - **Varied Encouragement:** Uses diverse positive reinforcement (Perfect! Bravo! Minunat!)
  - If student answers correctly, moves to next prerequisite with celebration
  - If student struggles, AI provides clear explanation with extra support
  - **Final Recap:** Reviews all learned concepts before the main explanation
  - AI provides comprehensive explanation of the original concept with references to prerequisites
  - **Motivational Closure:** Ends with encouragement and suggested next steps
  
- **Best for:** Students who want deeper understanding and prefer interactive, guided learning
- **Uses:** LangGraph workflow for state management and intelligent conversation flow

- **Example Flow:**
  ```
  Student: "I want to understand derivatives"
  AI: "To understand derivatives, we need to cover: 1) limits, 2) rate of change. 
       Let's start - what do you know about limits?"
  Student: [Provides answer]
  AI: [Evaluates, clarifies if needed, moves to next concept]
  [After prerequisites]
  AI: [Provides comprehensive derivative explanation with examples and graphs]
  ```

#### Technical Capabilities
- **Real-time streaming:** Responses stream token-by-token for natural conversation feel
- **Rich formatting:** 
  - Markdown for text structure
  - LaTeX for mathematical formulas (inline and display modes)
  - Interactive function graphs with multiple curves support
  - Color-coded graphs for comparing functions (e.g., function and its tangent)
- **Context retention:** Maintains conversation history for coherent follow-up discussions
- **Performance tracking:** Monitors time-to-first-token for quality assurance

#### Business Value
- Replicates private tutor experience at scale
- Two learning modes accommodate different learning styles
- 24/7 availability without scheduling constraints
- Consistent quality explanations across all topics
- Cost-effective compared to traditional tutoring (target: <50 RON/month vs 400-600 RON/month)

---

### 2. Vreau să rezolv o problemă (I Want to Solve a Problem)

**Status:** ✅ Implemented (first version)  
**Implementation Date:** January 2026

An AI-assisted flow for students who have a concrete exam problem (usually on paper or in a photo) and want help understanding and solving it, step by step.

#### What it does
- Lets students **upload a picture** of a math problem (mobile or web).
- Automatically extracts the **problem text (OCR)** and builds context around it.
- Starts the conversation with an **assistant message** that:
  - Reflects the detected problem statement.
  - Asks the student whether they want a full solution or just hints.
- Continues as a **chat-based problem-solving session**:
  - Students can ask for hints, explanations of specific steps, or full solutions.
  - The AI can adjust between detailed reasoning and high-level guidance.

#### How it works (business-level)
- **Student journey:**
  1. Opens “Vreau să rezolv o problemă”.
  2. Uploads a photo of a math problem.
  3. Sees the image preview and the AI’s first response summarizing the problem.
  4. Chooses how much help they want (hint vs full solution).
  5. Asks follow-up questions until they fully understand the solution.

- **Behind the scenes:**
  - The backend runs OCR and interprets the problem.
  - The AI model generates a structured first answer tailored to that problem.
  - The Flutter app keeps the **image + conversation** together in a single session.

#### Integration with conversation history
- Each “Vreau să rezolv o problemă” session is stored as a `problem_solving` conversation in Supabase.
- The **first stored message** is the assistant’s initial message based on the uploaded image.
- All further questions and answers are stored as additional messages in the same conversation.
- The **conversation sidebar**:
  - Shows a list of past problem-solving sessions.
  - Lets students reopen an old problem and continue the discussion.
  - When reopening, the app loads the **entire message history from the database** and sends it as context to the AI, so follow-up questions always see the full prior conversation (within model token limits).
  - Allows renaming conversation titles for easier navigation (e.g., “Integrals – variantă 2023”).

#### Business Value
- Helps students **bridge the gap between theory and real exam tasks**.
- Reduces friction: no need to type long problems; a quick photo is enough.
- Encourages **productive struggle**:
  - Students can start with a hint, attempt the problem, and come back for more detailed help.
- Builds a **history of solved problems** for reflection, revision, and teacher review.

#### Similar problems (RAG)
- After the first assistant message (from OCR), students can ask for **problems similar** to the one on the photo; the app calls a dedicated backend endpoint and shows numbered suggestions.
- Choosing a suggestion continues the **same** solve flow (full solution vs hint, follow-up chat).
- **Open in Rezolvare from Simulari:** After a simulation, students can open similar problems in a new `problem_solving` conversation whose first turn is that suggestion list (see Simulari below).

---

### 3. Simulari (Bac-style exam simulation)

**Status:** ✅ Implemented (MVP)  
**Implementation Date:** April 2026 (ongoing refinements)

A practice exam experience aligned with the Romanian Bac structure: timed session, problem statements with LaTeX, self-grading against a marking guide, and history of past attempts.

#### What it does
- **Simulare tab:** Generate a random Bac-style paper (subject slots filled from `exam_problems`), **3-hour** session timer, optional **finish** action, then per-problem score entry and submit to the backend for persisted totals.
- **Istoric tab:** Chart and list of **submitted** simulations; open a past run to review statements, barem, and saved scores (read-only).
- **Probleme similare (per problem):** On each problem card, after the live exam is **finished** or when viewing a simulation from **Istoric**, an action opens **vector-based similar problems** (same engine as Rezolvare). A bottom sheet shows the suggestions with **proper LaTeX rendering**; the student can **open in “Vreau să rezolv o problemă”** so the first assistant message lists the five suggestions and the usual solve flow applies.

#### Business value
- Connects **full-paper practice** with **targeted extra practice** on related items.
- Reuses one RAG pipeline for both Rezolvare and Simulari, consistent monthly quota behaviour.

---

## 💾 Supabase Integration & Conversation History

### January 28, 2026 - Persistent Conversations via Supabase

**What Changed:**
- **Supabase backend integration:**
  - Added a local Supabase project to manage structured data (users, conversations, simulations, etc.).
  - Flutter app talks directly to Supabase REST API for conversation storage (configurable URL + API key).
  - All Supabase credentials and URLs are centralized in a single Flutter config file for easy environment switching.

- **Database schema for tutoring flows:**
  - `users`: core user profile (email, name, study_year, auth linkage).
  - `conversations`: one row per tutoring thread, with:
    - `user_id` – owner of the conversation.
    - `type` – one of:
      - `problem_solving` – “Vreau să rezolv o problemă”.
      - `clarify` – Clarify Once (direct explanation).
      - `clarify_steps` – Clarify Step-by-Step (guided learning).
    - `title`, `school_subject`, `created_at` metadata.
  - `conversation_messages`:
    - One row per message in a conversation.
    - `speaker` field distinguishes `user` vs `assistant` messages.
    - Stores the full message content and timestamp.
  - **Exam simulation and content:**
    - `exam_problems`, `exam_simulations`, `exam_simulation_problems`,
      `exam_grades`, `scoring_scales`.
  - **Vector search (RAG) for similar problems:**
    - `documents` stores embedded problem statements (`vector(1024)`), indexed by the ingestion pipeline.
    - SQL function `public.match_documents(query_embedding, match_count)` must exist in the project (see `backend/sql/match_documents_rpc.sql`) for PostgREST RPC used by the AI backend.

- **Row Level Security (RLS):**
  - Conversations and messages are protected so a user can only see/update
    their own data (via Supabase `auth_id` → `users` mapping).
  - For local testing, all conversations are currently written under `user_id = 1`,
    but the policies are ready for real authentication.

**Conversation Experience in the App:**
- **Unified conversation history sidebar:**
  - Each major AI flow now has a sidebar showing previous conversations:
    - “N-am înțeles la clasă” → tabs use `clarify` / `clarify_steps`.
    - “Vreau să rezolv o problemă” → uses `problem_solving`.
  - Students can:
    - Browse past conversations per mode.
    - Click to load the full message history into the current chat.
    - Edit conversation titles directly from the sidebar:
      - Custom titles are stored in the `name` column in Supabase.
      - When `name` is empty, the app falls back to the first message/title for display.

- **When conversations are created & saved:**
  - **Clarify Once / Step-by-Step:**
    - A new conversation is created only when the student sends the *first* message
      in a blank chat.
    - That first user message is stored as a `user` message in `conversation_messages`.
    - Each full AI response (after streaming completes) is stored as an `assistant` message.
  - **Vreau să rezolv o problemă:**
    - The conversation is created when the image is processed and the AI sends
      the first assistant message based on the OCR result.
    - That initial assistant message becomes the first stored message of the conversation.
    - All subsequent user questions and AI responses are appended to the same conversation.

**Business Impact:**
- Students can **return to previous sessions** instead of starting from scratch every time.
- Teachers/parents (future) can review how a student interacted with the tutor over time.
- Enables future analytics:
  - Time spent per topic.
  - Common misconceptions per user or cohort.
  - Quality monitoring of assistant responses.

---

## 🔄 Recent Changes

### April 2026 - Simulari, RAG router, and similar problems
**What changed:**
- **Simulari** in the Flutter app: Istoric + Simulare tabs, generation, timer, self-scoring, submission, and review of past simulations.
- **Similar problems:** Shared **RAG** feature in the AI backend under **`POST /rag/suggest-problem`** (embed query, `match_documents` in Supabase); used from Rezolvare and from each Simulari problem card (with LaTeX in the result sheet).
- **Deep link to Rezolvare:** From Simulari, opening similar problems can start a new `problem_solving` conversation with the suggestion list as the first assistant turn.

**Business impact:** Students can move from mock exam items to focused practice without leaving the product narrative (simulation → related drills → solve chat).

### January 26, 2026 - Step-by-Step Learning Enhancements (Quick Wins)
**What Changed:**
- **Progress Tracking:** Students now see their progress through prerequisites (e.g., "Concept 2/3")
- **Learning Journey Preview:** At the start, students see a roadmap of all concepts they'll learn
- **Varied Encouragement:** AI uses diverse positive reinforcement (Perfect! Bravo! Minunat! etc.)
- **Confidence Detection:** AI adjusts tone based on student certainty ("cred că", "nu sunt sigur")
- **Final Recap:** Comprehensive summary of learned concepts before final explanation
- **Motivational Closure:** Each learning session ends with encouragement and next steps

**Business Impact:**
- Improved student engagement and motivation
- Clearer learning path visibility
- More personalized tutoring experience
- Better mimics real human tutor interactions

### January 26, 2026 - Feature Renaming for Clarity
**What Changed:**
- Backend router files renamed for better code maintainability:
  - `explica.py` → `clarify_once.py`
  - `guided_learning.py` → `clarify_step_by_step.py`
- API endpoints updated for consistency:
  - `/clarify/stream` → `/clarify/once-stream`
  - `/clarify/guided-stream` → `/clarify/step-by-step-stream`

**Business Impact:**
- None - functionality remains identical
- Internal codebase is more maintainable
- API naming is more intuitive for future development

---

## 📊 Feature Roadmap Status

| Feature | Status | Priority | Notes |
|---------|--------|----------|-------|
| N-am înțeles la clasă | ✅ Complete | P1 | Both modes fully functional |
| Vreau să rezolv o problemă | ✅ Complete | P1 | OCR, chat, similar problems (RAG) |
| Simulari (exam simulation) | ✅ Complete (MVP) | P1 | Timer, scoring, Istoric, similar problems per item |
| Similar problems (RAG) | ✅ Complete | P1 | `/rag/suggest-problem`; Simulari + Rezolvare |
| Progressive Hints | 🔄 Planned | P1 | Broader hint ladder (may overlap solve flow) |

**Legend:**
- ✅ Complete - Feature is live and tested
- 🔄 Planned - Next in development pipeline
- 📋 Backlog - Planned for future implementation
- ⏸️ Paused - Development temporarily suspended

---

## 🎯 Key Metrics & Performance

### User Experience
- **Response Time:** First token typically appears within 1-3 seconds
- **Accuracy:** Responses based on Gemini 2.0 Flash model
- **Availability:** 24/7 (dependent on backend uptime)

### Technical Performance
- **Backend:** FastAPI with async/streaming support
- **AI Model:** Google Gemini 2.0 Flash (temperature: 0.0 for consistency)
- **Scalability:** Stateless design allows horizontal scaling

---

## 💡 How Features Work Together

- **Clarify** and **Rezolvare** are separate chat surfaces with shared patterns (streaming, LaTeX, Supabase history).
- **Simulari** adds full-paper practice; **similar problems** on each item reuse the same RAG endpoint as Rezolvare and can **hand off** into a new Rezolvare conversation.
- **Example study path:** Run a Simulari session → review marks → open similar problems for a weak item → work through one suggestion with hints or full solution in Rezolvare → return to Clarify for a concept gap if needed.

---

## 📝 Feature Update Guidelines

When updating this document:

1. **For New Features:**
   - Add to "Implemented Features" section
   - Update roadmap status table
   - Add implementation date
   - Explain business value

2. **For Feature Changes:**
   - Add entry to "Recent Changes" section
   - Update relevant feature description
   - Note business impact (if any)

3. **Keep Business-Focused:**
   - Focus on WHAT users can do
   - Explain WHY it matters
   - Avoid technical implementation details (save for technical docs)
   - Use examples to illustrate functionality

---

## 📞 Feature Support

For questions about feature implementation or to report issues:
- **Technical Issues:** Check backend logs and Flutter console
- **Feature Requests:** Document in project backlog
- **Bug Reports:** Include steps to reproduce, expected vs actual behavior

---

## 🔮 Next Steps

**Immediate Priorities:**
1. Gather user feedback on Simulari and similar-problems handoff to Rezolvare
2. Progressive Hints / deeper step scaffolding where it adds value beyond current solve flow
3. Monitor RAG quality (index coverage, embedding refresh) and quota usage

**Future Enhancements:**
1. Expand to other subjects beyond math
2. Consistent Romanian UI copy across the app (product-facing strings)
3. User progress analytics across Simulari + conversations
4. Personalized learning recommendations

---

*This document should be reviewed and updated at the end of each development sprint or when significant features are completed.*
