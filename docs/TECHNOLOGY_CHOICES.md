# Technology Choices

This document maps our requirements to specific technology decisions, explaining the rationale for each choice.

> **Related Documents:**
> - [DATA_ARCHITECTURE.md](DATA_ARCHITECTURE.md) - Data structures, storage, and context assembly
> - [STORY_SYSTEM.md](STORY_SYSTEM.md) - Story design concepts

---

## Core Stack Overview

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **AI Agents** | Google ADK (Python) | Native Gemini integration, memory system, multi-agent orchestration |
| **Story Engine** | Custom Python module | Story-aware coordination layer above ADK |
| **LLM** | Gemini 2.5 Flash/Pro | Cost-efficient, fast, great for conversational agents |
| **Memory Bank** | Vertex AI Memory Bank | Semantic search over conversation history, per-user isolation |
| **Backend API** | FastAPI (Python) | Async-first, works well with ADK, modern Python |
| **Database** | PostgreSQL | Reliable, scales well, good for complex queries |
| **Queue/Scheduler** | Redis + Huey | Lightweight task queue, simpler than Celery for MVP |
| **Trigger Engine** | Custom evaluator (MVP) | Condition-based triggers (`trust >= 30 AND days >= 2`) |
| **Landing/Registration** | FastAPI + Jinja2 | Simple server-rendered pages, no frontend framework |
| **Story Pages** | Separate simple apps | Built per subdomain as story requires |
| **Email Service** | Mailgun | Deliverability + inbound webhooks |
| **SMS Service** | Twilio | Reliable SMS delivery + inbound webhooks |
| **Containerization** | Docker + Docker Compose | Single-command deployment, self-hostable |

**Hosting Model:** Hybrid - Self-host core infrastructure (app, DB, Redis), use Google Cloud for AI services (Gemini API, Memory Bank).

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                   ARGent                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  MAIN SITE (argent.io)                       STORY PAGES (subdomains)       │
│  ┌────────────────────────────┐              ┌────────────────────────┐     │
│  │  Landing + Registration    │              │  evidence.argent.io    │     │
│  │  (FastAPI + Jinja2)        │              │  (Simple HTML/CSS)     │     │
│  │  - / (landing)             │              │  - Key validation      │     │
│  │  - /register               │              │  - Evidence view       │     │
│  │  - /verify                 │              │  - Access logging      │     │
│  │  - /start                  │              └────────────────────────┘     │
│  └────────────────────────────┘              (More subdomains as needed)    │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  EXTERNAL SERVICES (webhooks into our API)                                  │
│  ┌─────────────────┐     ┌─────────────────┐                                │
│  │  Email Service  │     │  SMS Service    │                                │
│  │  (Mailgun)      │     │  (Twilio)       │                                │
│  │  - Send emails  │     │  - Send SMS     │                                │
│  │  - Inbound hook │     │  - Inbound hook │                                │
│  └────────┬────────┘     └────────┬────────┘                                │
│           │                       │                                          │
│           └───────────┬───────────┘                                          │
│                       ▼                                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         FASTAPI SERVER                                 │  │
│  │                                                                        │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │  │
│  │  │                       STORY ENGINE                                │ │  │
│  │  │  - Thread state machine    - Trigger evaluator                   │ │  │
│  │  │  - Pacing controller       - Agent coordinator                   │ │  │
│  │  └──────────────────────────────────────────────────────────────────┘ │  │
│  │                                │                                       │  │
│  │  ┌─────────────────────────────┼─────────────────────────────────────┐│  │
│  │  │                       GOOGLE ADK                                   ││  │
│  │  │  ┌───────────┐  ┌───────────┐  ┌───────────┐                      ││  │
│  │  │  │  Intent   │  │   Ember   │  │   Miro    │                      ││  │
│  │  │  │  Agent    │  │  (Email)  │  │ (Telegram)│                      ││  │
│  │  │  └───────────┘  └───────────┘  └───────────┘                      ││  │
│  │  │                                                                    ││  │
│  │  │  ┌────────────────────────────────────────────────────────────┐   ││  │
│  │  │  │  State: Session | user: | app: | MemoryBank               │   ││  │
│  │  │  └────────────────────────────────────────────────────────────┘   ││  │
│  │  └────────────────────────────────────────────────────────────────────┘│  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                │                                              │
│              ┌─────────────────┼─────────────────┐                           │
│              ▼                 ▼                 ▼                           │
│       ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                   │
│       │ PostgreSQL  │   │    Redis    │   │    Huey     │                   │
│       │             │   │   (cache)   │   │  (workers)  │                   │
│       └─────────────┘   └─────────────┘   └─────────────┘                   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Services Summary

| Service | Purpose |
|---------|---------|
| `app` | FastAPI + Landing/Registration + Story Engine + ADK Agents |
| `worker` | Huey workers for scheduled messages and trigger evaluation |
| `postgres` | Database |
| `redis` | Cache + Huey task broker |

**Total: 4 containers** (down from 6)

---

## AI Agent Layer

### Google ADK + Story Engine

ADK handles individual agent conversations. The **Story Engine** coordinates the narrative.

```
┌─────────────────────────────────────────────────────────────┐
│                      STORY ENGINE                            │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Responsibilities:                                     │  │
│  │  - Load story configuration (YAML)                     │  │
│  │  - Manage thread state machines                        │  │
│  │  - Evaluate triggers when state changes                │  │
│  │  - Decide which agent should speak                     │  │
│  │  - Control pacing based on engagement                  │  │
│  │  - Handle inter-agent awareness                        │  │
│  └───────────────────────────────────────────────────────┘  │
│                            │                                 │
│         ┌──────────────────┼──────────────────┐             │
│         ▼                  ▼                  ▼             │
│  ┌────────────┐     ┌────────────┐     ┌────────────┐      │
│  │   Ember    │     │    Miro    │     │   Future   │      │
│  │  (Email)   │     │   (SMS)    │     │   Agents   │      │
│  └────────────┘     └────────────┘     └────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### ADK State Management

ADK provides state prefixes for different scopes:

| Prefix | Scope | Use Case |
|--------|-------|----------|
| `temp:` | Current request only | In-progress calculations |
| (none) | Current session | Conversation context |
| `user:` | Across all sessions for user | Player state, relationships |
| `app:` | Global across all users | World facts, shared state |

**Our Usage:**
```python
# In ADK callbacks/tools
context.state["user:trust_elena"] = 45           # Player's trust in Elena
context.state["user:thread_progress"] = {...}    # Thread states
context.state["app:world_event_occurred"] = True # Global fact
context.state["temp:draft_response"] = "..."     # Temporary
```

### ADK Callbacks for Validation

```python
from google.adk.agents import LlmAgent, CallbackContext

def validate_character_response(
    callback_context: CallbackContext,
    llm_response: LlmResponse
) -> Optional[LlmResponse]:
    """Runs after model generates, before sending."""
    text = llm_response.content.parts[0].text

    # Check for character breaks
    if contains_meta_reference(text):
        return regenerate_with_note("Avoid breaking character")

    # Check for impossible knowledge
    character = callback_context.state.get("current_character")
    if reveals_unknown_info(text, character):
        return regenerate_with_note("Character doesn't know this")

    return None  # Accept as-is

elena_agent = LlmAgent(
    model="gemini-2.5-pro",
    name="elena",
    instruction="...",
    after_model_callback=validate_character_response
)
```

---

## AI Message Pipeline

When a player sends a message, it flows through this pipeline:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  1. INTENT EXTRACTION                                                    │
│     Agent: gemini-2.5-flash (fast, cheap)                               │
│     Input: Player message                                                │
│     Output (structured):                                                 │
│       intent: "question" | "statement" | "request" | "emotional"        │
│       sentiment: "positive" | "neutral" | "negative"                    │
│       topics: ["facility_7", "elena_trust"]                             │
│       key_info: ["player believes marcus over elena"]                   │
└────────────────────────────────────────┬────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  2. STATE UPDATE (Ripple Effects)                                        │
│     - Apply ripple rules based on intent                                 │
│     - Update trust levels, knowledge, etc.                               │
│     - Check if any triggers now match                                    │
└────────────────────────────────────────┬────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  3. CONTEXT ASSEMBLY                                                     │
│     Load: character config, world state, relationship, thread context,  │
│           recent conversation, relevant memories, urgency level         │
└────────────────────────────────────────┬────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  4. RESPONSE GENERATION                                                  │
│     Agent: gemini-2.5-pro (quality matters)                             │
│     System prompt built from context                                     │
│     Generate response in character                                       │
└────────────────────────────────────────┬────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  5. VALIDATION (after_model_callback)                                    │
│     - No character breaks                                                │
│     - No impossible knowledge                                            │
│     - No meta-references                                                 │
│     - Appropriate length                                                 │
│     → Retry if validation fails                                          │
└────────────────────────────────────────┬────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  6. SCHEDULING                                                           │
│     - Calculate delay based on character personality                     │
│     - Queue for delivery (Celery)                                        │
│     - Add typing indicator timing                                        │
└─────────────────────────────────────────────────────────────────────────┘
```

### Intent Extraction Agent

```python
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent

class PlayerIntent(BaseModel):
    intent: str = Field(description="question, statement, request, or emotional")
    sentiment: str = Field(description="positive, neutral, negative, or hostile")
    topics: list[str] = Field(description="Key topics mentioned")
    key_info: list[str] = Field(description="Important facts/opinions revealed")
    requires_response: bool

intent_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="intent_extractor",
    instruction="""Analyze the player's message. Extract:
- Their intent (are they asking, stating, requesting, or expressing emotion?)
- Their sentiment (how do they feel?)
- Key topics mentioned
- Any important information they revealed
- Whether this needs a response""",
    output_schema=PlayerIntent,
    output_key="player_intent"
)
```

---

## Trigger & Condition System

### The Problem with Time-Only Scheduling

Celery Beat handles: "Send message at 9am Monday"

But we need: "Send message when trust >= 30 AND 2 days since first contact"

### Solution: Hybrid Scheduling

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        SCHEDULING ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  TIME-BASED (Celery Beat)              CONDITION-BASED (Event-Driven)  │
│  ─────────────────────────             ───────────────────────────────  │
│  - Weekly check-ins                    - State change → Evaluate rules  │
│  - Scheduled story events              - If matched → Execute action    │
│  - Inactivity checks (every hour)                                       │
│                                                                         │
│  ┌─────────────┐                      ┌─────────────────────────────┐  │
│  │ Celery Beat │ ──→ Periodic tasks   │   Trigger Evaluator         │  │
│  └─────────────┘                      │   - Runs on state change    │  │
│                                       │   - Checks all active rules │  │
│                                       │   - Queues matched actions  │  │
│                                       └─────────────────────────────┘  │
│                                                     ▲                   │
│                                                     │                   │
│                                        ┌────────────┴────────────┐     │
│                                        │    State Change Hook    │     │
│                                        │  (After message, action)│     │
│                                        └─────────────────────────┘     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Trigger Evaluator (MVP)

Simple Python evaluator for conditions:

```python
class TriggerEvaluator:
    def evaluate(self, condition: dict, player_state: dict) -> bool:
        match condition:
            # Simple comparisons
            case {"field": field, "op": ">=", "value": value}:
                return get_nested(player_state, field) >= value

            # Milestone checks
            case {"milestone": milestone_id}:
                return milestone_id in player_state.get("milestones", [])

            # Time-based
            case {"days_since": event, "op": op, "value": days}:
                event_time = player_state.get("events", {}).get(event)
                if not event_time:
                    return False
                elapsed = (now() - event_time).days
                return compare(elapsed, op, days)

            # Compound conditions
            case {"all": conditions}:
                return all(self.evaluate(c, player_state) for c in conditions)

            case {"any": conditions}:
                return any(self.evaluate(c, player_state) for c in conditions)

# Usage in story config (YAML):
# triggered_by:
#   all:
#     - field: "relationships.elena.trust"
#       op: ">="
#       value: 30
#     - days_since: "first_contact"
#       op: ">="
#       value: 2
```

---

## Communication Layer

### Email

| Component | Technology | Notes |
|-----------|------------|-------|
| Sending | `aiosmtplib` | Async SMTP, works with any provider |
| Receiving | `aioimaplib` | Async IMAP for polling replies |
| Templating | Jinja2 | HTML email templates |
| Parsing | `mail-parser` | Extract reply content from threads |

### SMS (Twilio)

| Feature | Implementation |
|---------|----------------|
| Phone number | Dedicated Twilio number for Miro agent |
| Webhooks | FastAPI endpoint `/webhook/twilio` |
| Inbound SMS | Twilio POSTs form data with signature |
| MMS support | Media URLs for images/documents |
| Signature verification | HMAC-SHA1 with auth token |

**Webhook Architecture:**
```
┌─────────────────────────────────────────┐
│  FastAPI Server                         │
│  ├─ /webhook/mailgun  → Email (Ember)   │
│  ├─ /webhook/twilio   → SMS (Miro)      │
│  └─ ...                                 │
└─────────────────────────────────────────┘
```

---

## Database Layer

### PostgreSQL with SQLAlchemy (async)

**Design Principle:** Database stores structured/queryable data only. Message content lives in Memory Bank.

For complete schema, see [DATA_ARCHITECTURE.md](DATA_ARCHITECTURE.md#database-schema-refined).

**Key Tables:**
| Table | Purpose |
|-------|---------|
| `players` | Identity, verification, settings |
| `player_keys` | The cryptic key + access limits |
| `key_access_log` | Every access attempt logged |
| `player_trust` | Current trust scores per agent |
| `trust_events` | Trust changes (delta + reason) |
| `player_knowledge` | Extracted facts (natural language) |
| `story_milestones` | Story progress tracking |
| `messages` | **Metadata only** - no content |
| `triggers` | Loaded from YAML, cached |
| `trigger_history` | When triggers fired |

**Important:** The `messages` table stores metadata (id, timestamp, agent, direction, channel) but **not content**. Content lives in:
- ADK Session (recent 8-10 messages)
- Memory Bank (full history, semantic searchable)

---

## Web Layer

### Main Site (Landing + Registration)

**Choice: FastAPI + Jinja2 Templates**

Simple server-rendered pages. No frontend framework needed.

| Page | Purpose |
|------|---------|
| `/` | Landing page - what is ARGent? |
| `/register` | Email + Telegram signup form |
| `/verify/email` | Email verification callback |
| `/verify/telegram` | Telegram verification instructions |
| `/start` | "Start Game" button → triggers story |

**Tech:**
- Jinja2 templates with Tailwind CSS
- Simple form submissions
- No JavaScript framework required
- Mobile-friendly responsive design

### Story Pages (Subdomains)

Built separately as story requires. Each is a simple standalone page.

| Subdomain | Purpose | Tech |
|-----------|---------|------|
| `evidence.argent.io` | Corporate evidence system | Simple HTML/CSS + FastAPI backend |
| (future) | Other story elements | Built when needed |

**Evidence Dashboard specifically:**
- Styled as dated corporate intranet
- Key entry form → validation → evidence view
- Access logged to main database (for Ember visibility)
- Can be routes in main app or separate minimal app

---

## Evidence Dashboard (In-Fiction System)

A separate web application that players access with their unique key. This is **not** the player dashboard - it's a story element.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        EVIDENCE DASHBOARD                                │
├─────────────────────────────────────────────────────────────────────────┤
│  URL: evidence.argent.io (or subdomain)                                 │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      LOGIN PAGE                                  │   │
│  │   "ACCESS CREDENTIALS REQUIRED"                                  │   │
│  │   [ Enter Key: _________________________ ]                       │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                            │                                            │
│                            ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                   KEY VALIDATION                                 │   │
│  │   - Lookup key in player_keys table                             │   │
│  │   - Log access attempt (player_id, timestamp, IP)               │   │
│  │   - On valid: grant access + trigger "key_used" event           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                            │                                            │
│                            ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                   EVIDENCE VIEW                                  │   │
│  │   - Styled as internal corporate dashboard                       │   │
│  │   - Logs, documents, records (pre-authored content)              │   │
│  │   - "Someone else was here" hints for tension                    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Features

| Feature | Implementation |
|---------|----------------|
| Key generation | `secrets.token_urlsafe(24)` - unique per player |
| Key format | `a]@FyKbN2%nLp9$vR3xQ7mW` (looks cryptic, not obviously a URL) |
| Access logging | Every key entry attempt logged (success or failure) |
| Ember visibility | `key_access` events visible to Ember agent |
| Styling | Corporate intranet look (dated, internal) |
| Content | Static + dynamic elements based on story phase |

### Story Integration

When a key is used:
1. Log access with timestamp
2. Emit `key_used` event to Story Engine
3. Story Engine evaluates triggers
4. If `player.told_ember_wont_use = true` → Ember reacts (trust break)
5. If player returns to dashboard → "You accessed something" indicator

---

## Containerization

**Services:**
```yaml
services:
  app:          # FastAPI + Landing/Registration + Story Engine + ADK agents
  worker:       # Huey workers (message delivery, trigger evaluation)
  postgres:     # Database
  redis:        # Cache + Huey task broker
```

**Docker Compose (MVP):**
```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://redis:6379
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - MAILGUN_API_KEY=${MAILGUN_API_KEY}
      - TWILIO_ACCOUNT_SID=${TWILIO_ACCOUNT_SID}
      - TWILIO_AUTH_TOKEN=${TWILIO_AUTH_TOKEN}
    depends_on:
      - postgres
      - redis

  worker:
    build: .
    command: huey_consumer.py app.tasks.huey
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:16-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=argent
      - POSTGRES_USER=argent
      - POSTGRES_PASSWORD=${DB_PASSWORD}

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

**Total: 4 containers** (simplified from original 6-7)

---

## Technology Alternatives Considered

| Requirement | Chosen | Considered | Why Not |
|-------------|--------|------------|---------|
| AI Framework | Google ADK | LangGraph, CrewAI | ADK has native Gemini + memory, production-ready |
| LLM | Gemini 2.5 | GPT-4, Claude | Cost efficiency, ADK integration |
| Rules Engine | Custom evaluator | durable-rules, json-logic | Simpler for MVP, can migrate later |
| Backend | FastAPI | Django, Flask | Async-first, modern Python |
| Web UI | Jinja2 templates | Next.js, HTMX | Simplest for landing/registration pages |
| Queue | Huey | Celery, RQ, Dramatiq | Lightweight, built-in scheduling, Redis-based |
| Database | PostgreSQL | MongoDB, SQLite | Relational model fits our data, JSONB flexibility |
| Email | Mailgun | SMTP direct | Deliverability + inbound webhooks |
| SMS | Twilio | Other providers | Best docs, reliability, MMS support |

---

## Cost Estimates (Self-Hosted)

| Component | Cost | Notes |
|-----------|------|-------|
| Gemini API | ~$0.001/1K tokens | Very cost-efficient |
| VPS (DigitalOcean) | ~$24/month | 4GB RAM, handles 100+ players |
| Domain | ~$12/year | For email sender domains |
| Email (Mailgun) | Free tier | 5K emails/month |
| SMS (Twilio) | ~$0.0079/msg | Pay per message |

**Estimated cost per player per month:** ~$0.50-2.00 depending on engagement

---

## Sources

- [ADK State Management](https://google.github.io/adk-docs/sessions/state/)
- [ADK Callbacks](https://google.github.io/adk-docs/callbacks/types-of-callbacks/)
- [ADK Structured Outputs](https://saptak.in/writing/2025/05/10/google-adk-masterclass-part4)
- [ADK Multi-Agent Systems](https://cloud.google.com/blog/products/ai-machine-learning/build-multi-agentic-systems-using-google-adk)
- [Python State Machine](https://python-statemachine.readthedocs.io/en/develop/transitions.html)
- [Telegram Bot API](https://core.telegram.org/bots/api)
