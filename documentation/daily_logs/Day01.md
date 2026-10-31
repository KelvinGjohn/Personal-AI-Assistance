# Development Log — Day 01

| Field | Entry |
|-------|-------|
| Date | 31 October 2026 |
| Day | 1 of 29 |
| Phase | 1 — Planning and project foundation |

## Objectives
- Introduce the project and the problem it solves
- Define objectives, target users, scope and limitations
- Carry out a feasibility analysis
- Write the initial Software Requirements Specification
- Set the 29-day schedule

## Tasks completed
- Wrote the project proposal (purpose, problem, objectives, users, scope, feasibility, risks, technology choice)
- Wrote SRS v0.1 with 38 functional requirements (FR) and 15 non-functional requirements (NFR), prioritized with MoSCoW
- Listed the first data entities for the Day 4 database design
- Created the 29-day plan (`PLAN.md`)
- Created the repository with README and `.gitignore`

## Files created
- `README.md`
- `PLAN.md`
- `.gitignore`
- `documentation/SRS/Project_Proposal.md`
- `documentation/SRS/SRS_v0.1.md`
- `documentation/daily_logs/Day01.md`

## Files modified
- None (first day)

## Technologies used
- Markdown, Git

## Problems encountered and solutions
- The GitHub CLI is not installed, so the GitHub repository is created by hand on github.com and connected as `origin`.

## Test results
- No code yet, so there are no automated tests. Review check: every final acceptance criterion maps to at least one requirement (SRS section 6).

## Outstanding issues
- Choose the AI provider (decided on Day 12; the design stays provider-agnostic).
- Choose the hosting service (decided on Day 28).

## Git commit
- `Day 01: Initialize project requirements`

## Next day's objectives (Day 2)
- Explain the full system architecture and draw the architecture diagram (Mermaid)
- Set up the Python virtual environment and VS Code
- Create `requirements.txt` and `.env.example`

## Completion review
Day 1 is **complete**: the proposal, SRS v0.1 and schedule exist and are committed. Nothing on this day needed running code.
