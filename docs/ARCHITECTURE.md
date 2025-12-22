# Architecture

High-level system architecture and key technology decisions.

> **For implementation details, see the code.** This document explains *what* and *why*, not *how*.

---

## Tech Stack

| Layer | Technology | Why |
|-------|------------|-----|
| **AI Agents** | Google ADK (Python) | Native Gemini integration, memory system, multi-agent orchestration |
| **LLM** | Gemini 2.5 Flash | Cost-efficient, fast, great for conversational agents |
| **Backend** | FastAPI (Python) | Async-first, works well with ADK, modern Python |
| **Database** | PostgreSQL | Reliable, scales well, good for complex queries |
| **Queue** | Redis + Huey | Lightweight task queue, simpler than Celery for MVP |
| **Email** | Mailgun | Deliverability + inbound webhooks |
| **SMS** | Twilio | Reliable SMS delivery + inbound webhooks |
| **Web** | FastAPI + Jinja2 | Simple server-rendered pages, no frontend framework needed |

**Hosting Model:** Self-host core infrastructure (app, DB, Redis), use Google Cloud for AI services (Gemini API).

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                              ARGent                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  MAIN SITE                           EXTERNAL SERVICES               │
│  ├─ Landing + Registration           ├─ Mailgun (Email)              │
│  ├─ Web Inbox (dev/demo mode)        └─ Twilio (SMS)                 │
│  └─ Evidence Dashboard                        │                      │
│                                               ▼                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                      FASTAPI SERVER                           │   │
│  │  ┌────────────────────────────────────────────────────────┐  │   │
│  │  │  AGENTS (Google ADK)                                    │  │   │
│  │  │  ├─ Ember (Email)                                       │  │   │
│  │  │  └─ Miro (SMS)                                          │  │   │
│  │  └────────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                │                                     │
│              ┌─────────────────┼─────────────────┐                  │
│              ▼                 ▼                 ▼                  │
│       ┌─────────────┐   ┌─────────────┐   ┌─────────────┐          │
│       │ PostgreSQL  │   │    Redis    │   │    Huey     │          │
│       │ (state)     │   │   (cache)   │   │  (workers)  │          │
│       └─────────────┘   └─────────────┘   └─────────────┘          │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

**Containers:** 4 total (app, worker, postgres, redis)

---

## Storage Philosophy

**Principle:** Each system owns specific data types - no duplication.

| Data Type | Where | Why |
|-----------|-------|-----|
| Player identity, settings | PostgreSQL | Structured, queryable |
| Trust scores, milestones | PostgreSQL | Fast numeric queries for triggers |
| Message metadata | PostgreSQL | Tracking, delivery status |
| Message content | ADK Session | Working memory, no DB duplication |
| Conversation context | ADK Session | Recent 8-10 messages in memory |

**Design Decisions:**
- Database is source of truth for state
- Natural language for AI-facing data (player knowledge stored as sentences, not flags)
- Token-conscious context assembly (~2500 token budget per agent call)

---

## Key Decisions

### Why Google ADK?
- Native Gemini integration
- Built-in memory and session management
- Multi-agent orchestration support
- Production-ready, actively developed

### Why Huey over Celery?
- Lightweight, simpler configuration
- Built-in scheduling
- Redis-based (already using Redis)
- Sufficient for MVP scale

### Why No Frontend Framework?
- Landing/registration pages are simple forms
- Story happens in email/SMS, not on a website
- Jinja2 templates with Tailwind CSS are sufficient
- Less complexity, faster development

### Why Mailgun + Twilio?
- Proven deliverability
- Inbound webhooks for receiving replies
- Good documentation
- Free tiers for development

---

## Alternatives Considered

| Choice | Selected | Considered | Why Not |
|--------|----------|------------|---------|
| AI Framework | Google ADK | LangGraph, CrewAI | ADK has native Gemini + memory |
| LLM | Gemini 2.5 | GPT-4, Claude | Cost efficiency, ADK integration |
| Backend | FastAPI | Django, Flask | Async-first, modern |
| Queue | Huey | Celery, RQ | Simpler for MVP |
| Database | PostgreSQL | MongoDB, SQLite | Relational model fits our data |

---

## Cost Estimates

| Component | Cost | Notes |
|-----------|------|-------|
| Gemini API | ~$0.001/1K tokens | Very cost-efficient |
| VPS | ~$24/month | 4GB RAM handles 100+ players |
| Email | Free tier | Mailgun: 5K emails/month |
| SMS | ~$0.0079/msg | Twilio pay-per-message |

**Per player per month:** ~$0.50-2.00 depending on engagement
