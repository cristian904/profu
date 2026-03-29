---
name: planning
description: General rules to follow when in planning mode.
---

# Planning

## Instructions
- Plans live in plans/ at the project root. Each plan is a self-contained file named descriptively (e.g., plans/gift-tracking.md, plans/email-validation.md).   
- scan the current implementation and find similar patterns, don't reinvent the wheel
for every task
- breakdown the task into small sub-tasks to aid implementation
    - A task is too big when the reviewer needs to hold multiple unrelated concepts in their head to understand it, or when you'd struggle to write a clear 1-3 sentence summary of what it does.
    - There will be exceptions — some changes are inherently coupled and splitting them would create broken intermediate states. Use judgement. But the default should always be to ask "can this be split?"
- think of age-cases and ask how to handle them
- ask as many questions as possible before developing the plan, if there are unclear aspects
- more complex tasks require a diagram to better understand how the data flows
- testing should be the last plan step always
- find relevant documentation that would aid the implementation. For example, you have to plan for some supabase or langfuse integrations, you must first browse the library's documentation. Take you time on this, nobody knows it all.