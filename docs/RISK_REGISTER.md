# Risk Register: Profu Solo MVP Development

## Risk Assessment Matrix

| Risk ID | Risk Description | Probability | Impact | Severity | Status | Mitigation |
|---------|------------------|-------------|--------|----------|--------|------------|
| **RISK-001** | Time Constraints (5-7h/week) | High | High | **CRITICAL** | Active | Strict scope, use templates |
| **RISK-002** | Frontend Complexity | High | High | **HIGH** | Active | Web app, copy-paste components |
| **RISK-003** | Content Collection | Medium | Medium | **MEDIUM** | Active | Start small (20-30 problems) |
| **RISK-004** | Scope Creep | High | High | **HIGH** | Active | 2 features max, strict MVP |
| **RISK-005** | GPT-4 API Costs | Medium | Medium | **MEDIUM** | Active | Cache responses, monitor usage |
| **RISK-006** | Deployment Issues | Low | Medium | **MEDIUM** | Active | Use managed services |
| **RISK-007** | OCR Accuracy | Medium | Medium | **MEDIUM** | Active | Accept 80% accuracy for MVP |
| **RISK-008** | Burnout | Medium | High | **MEDIUM** | Active | Realistic timeline, breaks |

---

## Detailed Risk Analysis

### RISK-001: Time Constraints (5-7 hours/week)
**Category**: Resource  
**Probability**: High (100% - this is the constraint)  
**Impact**: High - May not complete MVP in 2 months  
**Severity**: **CRITICAL**

#### Description
Only 5-7 hours per week available. This is a hard constraint that limits what can be built.

#### Impact
- May not complete all planned features
- Quality might suffer
- Timeline might extend beyond 2 months

#### Mitigation Strategies

**Strategy 1: Strict Scope Management** (Critical)
- **2 features max**: Hints + Theory Bot only
- **No scope creep**: Resist adding features
- **MVP mindset**: Functional, not perfect
- **Defer everything else**: Post-MVP features

**Strategy 2: Use Templates & Copy-Paste**
- **Frontend**: shadcn/ui components (copy-paste)
- **Backend**: FastAPI templates
- **Save**: ~5-10 hours

**Strategy 3: Managed Services**
- **Database**: Supabase (no setup)
- **Hosting**: Railway/Vercel (one-click)
- **Save**: ~3-5 hours

**Strategy 4: GPT-4 Assistance**
- **Code generation**: Ask GPT-4 for snippets
- **Parsing**: Use GPT-4 Vision for problem extraction
- **Save**: ~3-5 hours

**Strategy 5: Simple Architecture**
- **No microservices**: Monolith is fine
- **No Docker**: Use managed services
- **Save**: ~5-8 hours

#### Contingency Plan
- **Reduce to 1 feature**: If time is tight, focus on Hints only
- **Extend timeline**: Add 1-2 weeks if needed
- **Simplify further**: Remove Theory Bot if necessary

#### Owner
Solo Developer

#### Status
**Active** - Ongoing constraint

---

### RISK-002: Frontend Complexity
**Category**: Technical  
**Probability**: High (70%)  
**Impact**: High - Frontend is not your strength  
**Severity**: **HIGH**

#### Description
Limited frontend expertise. Building a React app might take longer than expected.

#### Impact
- Frontend development slower than planned
- UI might be basic/ugly
- Integration issues
- Time overrun

#### Mitigation Strategies

**Strategy 1: Use Web App (Not Mobile)**
- **React web**: Easier than React Native
- **Browser-based**: No app store approval
- **Faster development**: ~5-10 hours saved

**Strategy 2: Copy-Paste Components**
- **shadcn/ui**: Beautiful components, copy-paste
- **Tailwind CSS**: Fast styling
- **Templates**: Use React templates
- **Save**: ~5-8 hours

**Strategy 3: Simple UI**
- **Functional, not beautiful**: Focus on working, not pretty
- **Basic styling**: Tailwind utilities
- **No animations**: Skip fancy effects
- **Save**: ~3-5 hours

**Strategy 4: Backend First**
- **Build backend first**: Your strength
- **Frontend last**: When backend is solid
- **API-first**: Frontend just consumes API

**Strategy 5: GPT-4 for Frontend Code**
- **Ask GPT-4**: Generate React components
- **Copy-paste**: Use generated code
- **Save**: ~2-4 hours

#### Contingency Plan
- **Use templates**: React admin templates
- **Simplify UI**: Even more basic
- **Focus on backend**: Make backend great, frontend minimal

#### Owner
Solo Developer

#### Status
**Active** - Mitigation in Week 6

---

### RISK-003: Content Collection
**Category**: Content  
**Probability**: Medium (50%)  
**Impact**: Medium - Need problems to test  
**Severity**: **MEDIUM**

#### Description
Need 20-30 math problems with barem. Collection and parsing might take time.

#### Impact
- Delays Week 1
- Blocks testing
- May need to reduce problem count

#### Mitigation Strategies

**Strategy 1: Start Small**
- **20-30 problems**: Enough for MVP
- **Not 100+**: Add more later
- **Manual collection**: Faster than automated

**Strategy 2: Use GPT-4 Vision**
- **Image to text**: GPT-4 Vision API
- **Parsing help**: GPT-4 extracts structure
- **Save**: ~2-3 hours

**Strategy 3: Simple Format**
- **JSON structure**: Easy to work with
- **Text files**: Simple storage
- **No complex parsing**: Keep it simple

**Strategy 4: Barem Matching with GPT-4**
- **GPT-4 matches**: Ask GPT-4 to match problems to barem
- **Manual verification**: Quick check
- **Save**: ~1-2 hours

#### Contingency Plan
- **Reduce to 15 problems**: Minimum viable
- **Use GPT-4 to generate**: Create similar problems
- **Start without barem**: Add later

#### Owner
Solo Developer

#### Status
**Active** - Week 1 task

---

### RISK-004: Scope Creep
**Category**: Project Management  
**Probability**: High (80%)  
**Impact**: High - Timeline overrun  
**Severity**: **HIGH**

#### Description
Temptation to add features: Similar Problems, Exam Simulator, better UI, etc.

#### Impact
- Timeline extends beyond 2 months
- MVP never launches
- Burnout from trying to do too much

#### Mitigation Strategies

**Strategy 1: Strict MVP Definition**
- **2 features only**: Hints + Theory Bot
- **Write it down**: Document what's NOT in MVP
- **Refer back**: When tempted, check MVP scope

**Strategy 2: Post-MVP List**
- **Create backlog**: List all future features
- **Don't start**: Until MVP is launched
- **Prioritize**: After MVP feedback

**Strategy 3: Time Boxing**
- **Stick to timeline**: 8 weeks max
- **Cut features**: If time runs out
- **Launch anyway**: Better to launch basic MVP than perfect never-launched app

**Strategy 4: "Good Enough" Mindset**
- **Functional, not perfect**: MVP is about learning
- **Iterate later**: Improve after launch
- **User feedback**: Let users guide improvements

#### Contingency Plan
- **Cut Theory Bot**: If time is tight, Hints only
- **Extend 1 week**: Maximum extension
- **Launch basic**: Better than nothing

#### Owner
Solo Developer

#### Status
**Active** - Ongoing vigilance needed

---

### RISK-005: GPT-4 API Costs
**Category**: Financial  
**Probability**: Medium (50%)  
**Impact**: Medium - May exceed budget  
**Severity**: **MEDIUM**

#### Description
GPT-4 API costs can add up. With limited usage, might be $20-50/month, but could be more.

#### Impact
- Unexpected costs
- Need to optimize usage
- May need to switch to cheaper model

#### Mitigation Strategies

**Strategy 1: Cache Responses**
- **Cache hints**: Don't regenerate same hints
- **Cache chat**: Store common answers
- **Save**: 50-70% cost reduction

**Strategy 2: Monitor Usage**
- **Track API calls**: Log all requests
- **Set alerts**: Warn if usage high
- **Optimize prompts**: Shorter prompts = cheaper

**Strategy 3: Use GPT-3.5 for Simple Tasks**
- **GPT-3.5**: Cheaper, good for simple tasks
- **GPT-4**: Only for complex (hints, analysis)
- **Save**: 50% cost reduction

**Strategy 4: Rate Limiting**
- **Limit per user**: Prevent abuse
- **Free tier limits**: For MVP testing
- **Upgrade later**: If needed

#### Contingency Plan
- **Switch to GPT-3.5**: If costs too high
- **Reduce features**: Less AI usage
- **Add usage limits**: For users

#### Owner
Solo Developer

#### Status
**Active** - Monitor throughout

---

### RISK-006: Deployment Issues
**Category**: Technical  
**Probability**: Low (30%)  
**Impact**: Medium - Can't launch  
**Severity**: **MEDIUM**

#### Description
Issues deploying to cloud: CORS, environment variables, database connections, etc.

#### Impact
- Can't launch MVP
- Time wasted debugging
- Frustration

#### Mitigation Strategies

**Strategy 1: Use Managed Services**
- **Railway/Render**: One-click deploy
- **Vercel/Netlify**: Automatic deployments
- **Supabase**: Managed database
- **Save**: Less setup, fewer issues

**Strategy 2: Deploy Early**
- **Week 2-3**: Deploy backend early
- **Test in production**: Find issues early
- **Iterate**: Fix as you go

**Strategy 3: Simple Setup**
- **No Docker**: Use managed services
- **No CI/CD**: Manual deploy is OK
- **Environment variables**: Use hosting UI

**Strategy 4: Documentation**
- **Follow tutorials**: Use official guides
- **Ask for help**: Stack Overflow, Discord
- **Test locally**: Before deploying

#### Contingency Plan
- **Use simpler hosting**: If issues persist
- **Deploy later**: If needed, extend timeline
- **Get help**: Ask community if stuck

#### Owner
Solo Developer

#### Status
**Active** - Mitigation in Week 2, 7

---

### RISK-007: OCR Accuracy
**Category**: Technical  
**Probability**: Medium (50%)  
**Impact**: Medium - Poor user experience  
**Severity**: **MEDIUM**

#### Description
Tesseract OCR might not be accurate enough. Handwritten text especially problematic.

#### Impact
- Poor user experience
- Users frustrated with errors
- Need manual correction

#### Mitigation Strategies

**Strategy 1: Accept Lower Accuracy for MVP**
- **80% accuracy**: Acceptable for MVP
- **Printed text only**: Skip handwritten
- **User can edit**: Allow manual correction

**Strategy 2: Image Preprocessing**
- **Contrast enhancement**: Improve OCR
- **Rotation correction**: Fix orientation
- **Noise reduction**: Clean images
- **Improve**: 10-15% accuracy gain

**Strategy 3: GPT-4 Vision as Backup**
- **GPT-4 Vision**: Better accuracy
- **More expensive**: Use for difficult cases
- **Hybrid**: Tesseract first, GPT-4 if fails

**Strategy 4: Manual Input Option**
- **Always allow**: User can type problem
- **Fallback**: If OCR fails
- **Better UX**: User has control

#### Contingency Plan
- **Manual input only**: If OCR too problematic
- **Improve later**: Post-MVP
- **Use GPT-4 Vision**: If budget allows

#### Owner
Solo Developer

#### Status
**Active** - Mitigation in Week 3

---

### RISK-008: Burnout
**Category**: Personal  
**Probability**: Medium (40%)  
**Impact**: High - Project abandonment  
**Severity**: **MEDIUM**

#### Description
Working 5-7 hours/week on side project for 2 months might lead to burnout.

#### Impact
- Project abandoned
- Incomplete MVP
- Loss of motivation

#### Mitigation Strategies

**Strategy 1: Realistic Timeline**
- **8 weeks**: Reasonable timeline
- **5-7 hours/week**: Not too much
- **Weekend focus**: Less pressure

**Strategy 2: Take Breaks**
- **Skip week if needed**: Health first
- **Don't force**: If not motivated, rest
- **Come back fresh**: Better than burnout

**Strategy 3: Celebrate Small Wins**
- **Week 2**: Backend deployed = win
- **Week 4**: Hints working = win
- **Week 6**: Frontend done = win
- **Momentum**: Build on successes

**Strategy 4: Lower Expectations**
- **MVP is basic**: That's OK
- **Not perfect**: Functional is enough
- **Iterate later**: Improve after launch

**Strategy 5: Have Fun**
- **Enjoy the process**: Learning is good
- **Your strengths**: Backend, AI - fun for you
- **Side project**: Not life-or-death

#### Contingency Plan
- **Extend timeline**: If needed, add weeks
- **Reduce scope**: Cut features if burning out
- **Pause**: Take break, come back later

#### Owner
Solo Developer

#### Status
**Active** - Monitor throughout

---

## Risk Monitoring & Review

### Review Frequency
- **Weekly**: Check risks during development
- **Per Phase**: Review at end of each week
- **Adjust**: Mitigation strategies as needed

### Escalation Process
1. **Low/Medium Risks**: Handle yourself
2. **High Risks**: Adjust scope/timeline
3. **Critical Risks**: Reduce MVP scope

### Risk Dashboard
Maintain mental checklist:
- Time constraints: Am I on track?
- Scope creep: Am I adding features?
- Frontend: Is it taking too long?
- Burnout: Am I getting tired?

---

## Risk Mitigation Summary

### Top 3 Risks (Priority Order):

1. **RISK-001: Time Constraints** - Strict scope, use templates, managed services
2. **RISK-004: Scope Creep** - 2 features max, write down exclusions
3. **RISK-002: Frontend Complexity** - Web app, copy-paste, simple UI

### Quick Wins:
- Use managed services (save 5-10 hours)
- Copy-paste components (save 5-8 hours)
- GPT-4 assistance (save 3-5 hours)
- Simple architecture (save 5-8 hours)

**Total Time Saved**: ~18-31 hours (almost a full week!)

---

## Success Factors

1. **Strict Scope**: 2 features, nothing more
2. **Use Templates**: Don't build from scratch
3. **Deploy Early**: Week 2-3, test in production
4. **Focus on Backend**: Your strength
5. **Simple Frontend**: Functional, not beautiful
6. **Iterate Later**: Improve after MVP launch

---

**Document Version**: 2.0 (Solo MVP)  
**Last Updated**: January 25, 2026  
**Developer**: Solo (Data Scientist/AI Engineer)
