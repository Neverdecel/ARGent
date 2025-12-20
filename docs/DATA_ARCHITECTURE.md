# Data Architecture

This document defines how data flows through the system, where it's stored, and how context is assembled for AI agents.

---

## Tech Stack Summary

| Component | Technology | Hosting |
|-----------|------------|---------|
| **Database** | PostgreSQL | Self-hosted (Docker) |
| **Cache/Queue** | Redis + Huey | Self-hosted (Docker) |
| **AI Framework** | Google ADK | Self-hosted (Docker) |
| **LLM** | Gemini 2.5 Pro/Flash | Google Cloud API |
| **Memory Bank** | Vertex AI Memory Bank | Google Cloud |
| **App Server** | FastAPI | Self-hosted (Docker) |

**Hybrid Model:** Self-host core infrastructure, use Google Cloud for AI services (Gemini + Memory Bank).

---

## Design Principles

1. **Database is source of truth** - All state lives in PostgreSQL, ADK state is a working cache
2. **Natural language for AI** - Player knowledge stored as sentences, not flags
3. **Immediate classification** - Every exchange is analyzed for state changes (Gemini Flash)
4. **Token-conscious context** - ~2500 token budget per agent call
5. **Per-user memory isolation** - ADK Memory Bank separates each player's memory by `user_id`

---

## Storage Layers

### Data Ownership Principle

Each system owns specific data types - **no duplication**:

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATA OWNERSHIP (Optimized)                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  POSTGRESQL (Structured, Query-able)                            │
│  ├─ Player identity & settings                                  │
│  ├─ Trust scores (current values)                               │
│  ├─ Trust events (delta + reason, NO full message content)      │
│  ├─ Milestones reached                                          │
│  ├─ Message METADATA only (id, time, agent, direction)          │
│  ├─ Classifications (extracted intent, sentiment, behaviors)    │
│  ├─ Player knowledge (extracted facts as sentences)             │
│  └─ Key access logs                                             │
│                                                                  │
│  MEMORY BANK (Conversation Content, Semantic Search)            │
│  ├─ Full message content (player + agent messages)              │
│  ├─ Session histories (auto-indexed)                            │
│  └─ Semantic retrieval for relevant past context                │
│                                                                  │
│  ADK SESSION (Working Context, Ephemeral)                       │
│  ├─ Current conversation (last 8-10 messages in memory)         │
│  ├─ Hydrated state from DB (trust, milestones)                  │
│  └─ Temporary processing data (classifications in progress)     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Layer 1: PostgreSQL (Structured Data Only)

Stores metadata, extracted insights, and query-able state. **No raw message content.**

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATABASE (Metadata Only)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PLAYER IDENTITY          GAME STATE           MESSAGE METADATA │
│  ├─ players               ├─ player_trust      ├─ messages      │
│  ├─ player_keys           ├─ trust_events      │   (NO content) │
│  └─ key_access_log        ├─ player_knowledge  └─ classtic-     │
│                           └─ story_milestones      ations       │
│                                                                  │
│  TRIGGERS & SCHEDULING                                           │
│  ├─ triggers (from YAML)                                        │
│  ├─ trigger_history                                              │
│  └─ scheduled_messages                                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Layer 2: ADK Session State (Working Context)

Hydrated from DB at session start, written back after each exchange.

```python
# ADK State Prefixes
session.state["current_agent"]           # Which agent is active
session.state["user:trust_ember"]        # Current trust score (from DB)
session.state["user:trust_miro"]         # Current trust score (from DB)
session.state["user:engagement_level"]   # active/casual/dormant
session.state["user:story_phase"]        # day_1/day_2/thursday/post_thursday
session.state["temp:intent_analysis"]    # Current message analysis
session.state["temp:pending_state_changes"]  # Changes to write to DB
```

### Layer 3: Vertex AI Memory Bank (Semantic Search)

Long-term memory for past conversations, hosted on Google Cloud, searchable by relevance.

```
┌─────────────────────────────────────────────────────────────────┐
│                  VERTEX AI MEMORY BANK                           │
├─────────────────────────────────────────────────────────────────┤
│  Automatically indexed for semantic search:                      │
│                                                                  │
│  - All message exchanges (player + agent)                        │
│  - Key moments flagged by classifier                             │
│  - Session summaries (generated at session end)                  │
│                                                                  │
│  Retrieved via: PreloadMemoryTool or search_memory(query)       │
│                                                                  │
│  Per-user isolation: Each player's memory is separate           │
│  Hosting: Google Cloud (VertexAiMemoryBankService)              │
└─────────────────────────────────────────────────────────────────┘
```

**Memory Bank Setup:**
```python
from google.adk.memory import VertexAiMemoryBankService

memory_service = VertexAiMemoryBankService(
    project="your-gcp-project",
    location="us-central1",
    agent_engine_id="phantom-protocol-memory"
)
```

---

## Database Schema (Refined)

### Core Tables

```sql
-- Players (unchanged)
CREATE TABLE players (
    id UUID PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    telegram_id BIGINT UNIQUE,
    telegram_username TEXT,
    timezone TEXT DEFAULT 'UTC',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    game_started_at TIMESTAMPTZ,  -- When player clicked "Start Game"
    email_verified BOOLEAN DEFAULT FALSE,
    telegram_verified BOOLEAN DEFAULT FALSE
);

-- Player Keys (with access limit)
CREATE TABLE player_keys (
    id UUID PRIMARY KEY,
    player_id UUID REFERENCES players(id),
    key_value TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    access_limit INT DEFAULT 5,     -- Max allowed accesses
    access_count INT DEFAULT 0,     -- Current access count
    first_accessed_at TIMESTAMPTZ   -- NULL until first use
);

-- Key Access Log (unchanged)
CREATE TABLE key_access_log (
    id UUID PRIMARY KEY,
    player_id UUID REFERENCES players(id),
    key_id UUID REFERENCES player_keys(id),
    accessed_at TIMESTAMPTZ DEFAULT NOW(),
    success BOOLEAN NOT NULL,
    ip_address TEXT,
    user_agent TEXT
);
```

### Trust System (Hybrid: Current + Events)

```sql
-- Current trust scores (fast reads for triggers)
CREATE TABLE player_trust (
    player_id UUID REFERENCES players(id),
    agent_id TEXT NOT NULL,  -- 'ember', 'miro'
    trust_score INT DEFAULT 0,  -- -100 to 100
    interaction_count INT DEFAULT 0,
    last_interaction_at TIMESTAMPTZ,
    PRIMARY KEY (player_id, agent_id)
);

-- Trust change log (audit trail + AI context)
CREATE TABLE trust_events (
    id UUID PRIMARY KEY,
    player_id UUID REFERENCES players(id),
    agent_id TEXT NOT NULL,
    delta INT NOT NULL,  -- +10, -15, etc.
    reason TEXT NOT NULL,  -- Natural language: "Player agreed with Ember's assessment"
    message_id UUID REFERENCES messages(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for recent trust events
CREATE INDEX idx_trust_events_player_recent
ON trust_events(player_id, created_at DESC);
```

### Player Knowledge (Natural Language)

```sql
-- What the player knows (as natural language sentences)
CREATE TABLE player_knowledge (
    id UUID PRIMARY KEY,
    player_id UUID REFERENCES players(id),
    fact TEXT NOT NULL,  -- "Player learned about the dashboard from Miro on Day 2"
    category TEXT,       -- 'dashboard', 'key', 'ember', 'miro', 'story'
    source_agent TEXT,   -- Who revealed this
    learned_at TIMESTAMPTZ DEFAULT NOW(),
    message_id UUID REFERENCES messages(id)  -- Which message taught this
);

-- Index for efficient context loading
CREATE INDEX idx_knowledge_player_category
ON player_knowledge(player_id, category);
```

### Story Milestones

```sql
-- Milestones reached (for trigger evaluation)
CREATE TABLE story_milestones (
    player_id UUID REFERENCES players(id),
    milestone_id TEXT NOT NULL,  -- 'key_email_sent', 'ember_first_contact', etc.
    reached_at TIMESTAMPTZ DEFAULT NOW(),
    context JSONB,  -- Optional metadata
    PRIMARY KEY (player_id, milestone_id)
);
```

### Messages (Metadata Only)

Message **content** lives in Memory Bank. Database stores only metadata and classification results.

```sql
-- Message metadata (NO content - content is in Memory Bank)
CREATE TABLE messages (
    id UUID PRIMARY KEY,
    player_id UUID REFERENCES players(id),
    agent_id TEXT,  -- NULL for system messages, 'ember'/'miro' for agents
    channel TEXT NOT NULL,  -- 'email', 'telegram', 'system'
    direction TEXT NOT NULL,  -- 'inbound', 'outbound'
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Reference to Memory Bank session
    session_id TEXT,  -- ADK session ID where content lives

    -- Delivery tracking
    delivered_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ,

    -- Classification results (extracted insights)
    classified_at TIMESTAMPTZ,
    classification JSONB  -- See structure below
);

-- Index for recent messages
CREATE INDEX idx_messages_player_recent
ON messages(player_id, created_at DESC);
```

**Why no content column?**
- Content lives in Memory Bank (semantic searchable)
- Recent messages accessed via ADK Session (already in memory)
- Avoids duplication and sync issues
- Classification extracts all structured insights we need

### Message Classification Structure

```json
{
  "intent": "question",           // question, statement, request, emotional
  "sentiment": "neutral",         // positive, neutral, negative, hostile
  "topics": ["key", "trust"],     // Topics mentioned
  "significance": "high",         // low, medium, high

  // Detected behaviors
  "behaviors": {
    "agrees_with_agent": false,
    "disagrees_with_agent": true,
    "shares_info_from_other": false,
    "lies_detected": false,
    "expresses_trust": false,
    "expresses_distrust": true
  },

  // Extracted facts (if any)
  "new_knowledge": [
    "Player expressed distrust of Ember's explanation"
  ],

  // Suggested state changes
  "state_changes": {
    "trust_ember": -10,
    "trust_miro": 0
  }
}
```

### Key Moments

Key moments are **not stored in DB** - they're flagged during classification and the session is immediately saved to Memory Bank where they're semantically indexed.

The classification result includes:
```json
{
  "is_key_moment": true,
  "key_moment_type": "trust_shift",
  "key_moment_summary": "Player expressed distrust after Ember's evasive response"
}
```

This summary is included in the session saved to Memory Bank, making it searchable.

---

## Context Assembly Pipeline

When an agent needs to respond, context is assembled from **three sources** with no duplication:

### Token Budget (~2500 tokens total)

```
┌─────────────────────────────────────────────────────────────────┐
│              AGENT CONTEXT BUDGET (Optimized)                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  FROM YAML (Static, Cached)               ~600 tokens            │
│  └─ Character definition (personality, voice, rules, examples)  │
│                                                                  │
│  FROM DATABASE (Structured State)         ~400 tokens            │
│  ├─ Trust scores (ember: 45, miro: 30)                          │
│  ├─ Recent trust events (last 3: reason text only)              │
│  ├─ Player knowledge (10-15 extracted facts)                    │
│  ├─ Milestones reached                                          │
│  ├─ Key access status                                           │
│  └─ Story phase                                                 │
│                                                                  │
│  FROM ADK SESSION (Recent Conversation)   ~800 tokens            │
│  └─ Last 8-10 messages (already in session memory)              │
│                                                                  │
│  FROM MEMORY BANK (Semantic Search)       ~300 tokens            │
│  └─ Relevant past interactions (via search_memory)              │
│                                                                  │
│  CURRENT INPUT + INSTRUCTIONS             ~400 tokens            │
│  ├─ New player message                                          │
│  └─ Generation constraints (urgency, length, tone)              │
│                                                                  │
│  TOTAL                                    ~2500 tokens           │
└─────────────────────────────────────────────────────────────────┘
```

### Query Pattern Summary

| Data Needed | Source | Why |
|-------------|--------|-----|
| Character personality | YAML file | Static, cached at startup |
| Trust scores | Database | Fast numeric queries for triggers |
| Recent trust reasons | Database | Extracted during classification |
| Player knowledge | Database | Extracted facts, not raw messages |
| Last 8-10 messages | ADK Session | Already in memory, no query needed |
| Relevant past context | Memory Bank | Semantic search finds related content |
| Message content | Memory Bank | Never query DB for message text |

### Context Assembly Code (Pseudocode)

```python
async def assemble_agent_context(
    player_id: str,
    agent_id: str,
    new_message: str
) -> AgentContext:
    """Assemble full context for agent response generation."""

    # 1. Load character definition (from YAML cache)
    character = load_character_yaml(agent_id)

    # 2. Load current state (from DB)
    trust = await db.get_trust(player_id, agent_id)
    trust_events = await db.get_recent_trust_events(player_id, agent_id, limit=3)
    milestones = await db.get_milestones(player_id)
    key_status = await db.get_key_status(player_id)
    story_phase = calculate_story_phase(player_id)

    # 3. Load player knowledge (from DB, filtered by relevance)
    knowledge = await db.get_player_knowledge(
        player_id,
        categories=get_relevant_categories(new_message),
        limit=15
    )

    # 4. Search Memory Bank for relevant past interactions
    memories = await memory_service.search_memory(
        query=f"{new_message} {agent_id}",
        user_id=player_id,
        limit=5
    )

    # 5. Recent conversation already in ADK session
    # (No DB query needed - messages are in session.events or session.history)
    recent_messages = session.get_recent_messages(limit=10)

    # 6. Build the prompt
    return AgentContext(
        character=character,
        state=CurrentState(
            trust=trust,
            trust_history=format_trust_events(trust_events),
            story_phase=story_phase,
            key_accessed=key_status.access_count > 0,
            key_accesses_remaining=key_status.access_limit - key_status.access_count,
            milestones=milestones
        ),
        knowledge=knowledge,
        memories=memories,
        conversation=recent_messages,
        new_message=new_message,
        instructions=get_generation_instructions(agent_id, story_phase)
    )
```

---

## Message Processing Pipeline

### Full Flow (Player Sends Message)

```
┌─────────────────────────────────────────────────────────────────┐
│                    MESSAGE PROCESSING PIPELINE                   │
└─────────────────────────────────────────────────────────────────┘

  PLAYER MESSAGE
       │
       ▼
┌──────────────────┐
│ 1. RECEIVE       │  Store metadata in DB (no content)
│    & ROUTE       │  Add to ADK session, identify target agent
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 2. CLASSIFY      │  Gemini Flash (~100 tokens)
│    (Immediate)   │  Extract intent, sentiment, behaviors
└────────┬─────────┘  Detect lies, trust signals, revelations
         │
         ▼
┌──────────────────┐
│ 3. UPDATE STATE  │  Apply trust changes
│                  │  Record new knowledge
└────────┬─────────┘  Check trigger conditions
         │
         ▼
┌──────────────────┐
│ 4. CHECK         │  Is this a key moment?
│    SIGNIFICANCE  │  If yes → flag in classification JSON
└────────┬─────────┘  Summary will be indexed in Memory Bank
         │
         ▼
┌──────────────────┐
│ 5. ASSEMBLE      │  Load character + state + knowledge
│    CONTEXT       │  + memories + recent conversation
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 6. GENERATE      │  Gemini Pro (quality response)
│    RESPONSE      │  Full agent context
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 7. VALIDATE      │  Check for character breaks
│                  │  Check for impossible knowledge
└────────┬─────────┘  Retry if needed
         │
         ▼
┌──────────────────┐
│ 8. SCHEDULE      │  Calculate response delay
│    DELIVERY      │  Queue for delivery
└────────┬─────────┘  Add typing indicators
         │
         ▼
┌──────────────────┐
│ 9. DELIVER       │  Send via email/telegram
│                  │  Store metadata in DB, content in session
└────────┬─────────┘  Classify agent message too
         │
         ▼
┌──────────────────┐
│ 10. SYNC TO      │  Add session to Memory Bank
│     MEMORY       │  For future semantic search
└──────────────────┘
```

---

## Classification Prompt (Gemini Flash)

```python
CLASSIFICATION_PROMPT = """
Analyze this player message in the context of an ARG conversation.

PLAYER MESSAGE:
{message}

CONVERSATION CONTEXT (last 3 messages):
{recent_context}

CURRENT STATE:
- Trust with {agent}: {trust_score}
- Story phase: {story_phase}

Respond with JSON:
{
  "intent": "question|statement|request|emotional",
  "sentiment": "positive|neutral|negative|hostile",
  "topics": ["list", "of", "topics"],
  "significance": "low|medium|high",
  "behaviors": {
    "agrees_with_agent": bool,
    "disagrees_with_agent": bool,
    "shares_info_from_other": bool,  // Mentions other agent
    "lies_detected": bool,  // Says something contradicting known facts
    "expresses_trust": bool,
    "expresses_distrust": bool
  },
  "new_knowledge": ["Natural language facts player revealed"],
  "state_changes": {
    "trust_{agent}": integer (-20 to +20)
  },
  "is_key_moment": bool,
  "key_moment_summary": "One sentence summary if key moment"
}
"""
```

---

## Sync Strategy: DB ↔ ADK

### Session Start

```python
async def hydrate_adk_session(player_id: str, session: Session):
    """Load DB state into ADK session at start."""

    # Load from DB
    ember_trust = await db.get_trust(player_id, 'ember')
    miro_trust = await db.get_trust(player_id, 'miro')
    phase = await calculate_story_phase(player_id)

    # Hydrate ADK session state
    session.state["user:trust_ember"] = ember_trust.trust_score
    session.state["user:trust_miro"] = miro_trust.trust_score
    session.state["user:story_phase"] = phase
    session.state["user:engagement_level"] = calculate_engagement(player_id)
```

### After Each Exchange

```python
async def persist_state_changes(player_id: str, session: Session, classification: dict):
    """Write ADK state changes back to DB."""

    # Apply trust changes
    for key, delta in classification["state_changes"].items():
        agent = key.replace("trust_", "")
        await db.update_trust(player_id, agent, delta, classification)

    # Record new knowledge
    for fact in classification["new_knowledge"]:
        await db.add_knowledge(player_id, fact, source_agent, message_id)

    # Key moments: classification stored in DB, content synced to Memory Bank
    # (No separate key_moments table - the classification JSON has the summary)
    if classification["is_key_moment"]:
        # Immediately sync session to Memory Bank for semantic indexing
        await memory_service.add_session_to_memory(player_id, session)
```

---

## Summary

| Data Type | Storage | Purpose |
|-----------|---------|---------|
| Player identity | PostgreSQL | Registration, auth |
| Trust scores | PostgreSQL + ADK | Triggers + context |
| Trust events | PostgreSQL | Audit + AI context (reason text only) |
| Player knowledge | PostgreSQL | Context assembly (extracted facts) |
| Milestones | PostgreSQL | Trigger evaluation |
| Message metadata | PostgreSQL | Tracking, delivery status |
| Message content | Memory Bank | Semantic search, context retrieval |
| Classifications | PostgreSQL | State changes, key moment flags |
| Recent context | ADK Session | Working memory (8-10 messages) |
| Long-term memory | Memory Bank | Full conversation content |
