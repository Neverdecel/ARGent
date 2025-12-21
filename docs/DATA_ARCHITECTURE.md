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
-- Players
CREATE TABLE players (
    id UUID PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    phone TEXT UNIQUE,  -- E.164 format: +1234567890
    timezone TEXT DEFAULT 'UTC',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    game_started_at TIMESTAMPTZ,  -- When player clicked "Start Game"
    email_verified BOOLEAN DEFAULT FALSE,
    phone_verified BOOLEAN DEFAULT FALSE
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
    channel TEXT NOT NULL,  -- 'email', 'sms', 'system'
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

### Token Budget (~2800 tokens total)

```
┌─────────────────────────────────────────────────────────────────┐
│          AGENT CONTEXT BUDGET (With Immersion State)            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  FROM YAML (Static, Cached)               ~600 tokens            │
│  ├─ Character definition (personality, voice, rules)           │
│  ├─ Ground truth facts (for claim validation)                  │
│  └─ Sharing rules (for inter-agent context)                    │
│                                                                  │
│  FROM DATABASE (Structured State)         ~500 tokens            │
│  ├─ Trust scores + recent events          (~150)                │
│  ├─ Player knowledge (15 facts)           (~150)                │
│  ├─ Milestones + story phase              (~50)                 │
│  └─ Immersion state                       (~150)                │
│      ├─ Lifecycle state + modifiers                             │
│      ├─ World exposure + spawn conditions                       │
│      └─ Inter-agent knowledge (what I learned from others)      │
│                                                                  │
│  FROM ADK SESSION (Recent Conversation)   ~800 tokens            │
│  └─ Last 8-10 messages (already in session memory)              │
│                                                                  │
│  FROM MEMORY BANK (Semantic Search)       ~400 tokens            │
│  ├─ Relevant past interactions            (~200)                │
│  └─ Recent claims by this agent           (~200)                │
│                                                                  │
│  CURRENT INPUT + INSTRUCTIONS             ~500 tokens            │
│  ├─ New player message                    (~100)                │
│  ├─ Generation constraints                (~200)                │
│  └─ Consistency constraints               (~200)                │
│      └─ "Do not contradict: [recent claims]"                    │
│                                                                  │
│  TOTAL                                    ~2800 tokens           │
└─────────────────────────────────────────────────────────────────┘
```

### Query Pattern Summary

| Data Needed | Source | Why |
|-------------|--------|-----|
| Character personality | YAML file | Static, cached at startup |
| Ground truth / sharing rules | YAML file | For claim validation, sharing eval |
| Trust scores | Database | Fast numeric queries for triggers |
| Recent trust reasons | Database | Extracted during classification |
| Player knowledge | Database | Extracted facts, not raw messages |
| Lifecycle state | ADK Session | Hydrated at start, affects behavior |
| Inter-agent knowledge | ADK Session | What this agent learned from others |
| World exposure | ADK Session | For spawn condition context |
| Last 8-10 messages | ADK Session | Already in memory, no query needed |
| Relevant past context | Memory Bank | Semantic search finds related content |
| Recent agent claims | Memory Bank | For consistency checking |
| Message content | Memory Bank | Never query DB for message text |

### Context Assembly Code (Pseudocode)

```python
async def assemble_agent_context(
    player_id: str,
    agent_id: str,
    new_message: str,
    session: Session
) -> AgentContext:
    """Assemble full context for agent response generation."""

    # 1. Load character definition (from YAML cache)
    character = load_character_yaml(agent_id)

    # 2. Load current state (from DB - most is cached in session)
    trust = session.state.get(f"user:trust_{agent_id}", 0)
    trust_events = await db.get_recent_trust_events(player_id, agent_id, limit=3)
    milestones = await db.get_milestones(player_id)
    key_status = await db.get_key_status(player_id)
    story_phase = session.state.get("user:story_phase")

    # 3. Load player knowledge (from DB, filtered by relevance)
    knowledge = await db.get_player_knowledge(
        player_id,
        categories=get_relevant_categories(new_message),
        limit=15
    )

    # 4. Get immersion state (from ADK session - already hydrated)
    lifecycle = session.state.get(f"agent:{agent_id}:lifecycle", "engaged")
    tone_modifier = session.state.get(f"agent:{agent_id}:tone", "normal")
    exposure = session.state.get("world:exposure", 0)

    # 5. Get inter-agent knowledge (what this agent learned from others)
    inter_agent_knowledge = []
    for other_agent in ['ember', 'miro']:
        if other_agent != agent_id:
            learned = session.state.get(f"agent:{agent_id}:learned_from:{other_agent}", [])
            if learned:
                inter_agent_knowledge.extend(learned)

    # 6. Search Memory Bank for relevant past interactions
    memories = await memory_service.search_memory(
        query=f"{new_message} {agent_id}",
        user_id=player_id,
        limit=5
    )

    # 7. Get recent claims for consistency checking
    recent_claims = session.state.get("cache:recent_claims", [])
    agent_claims = [c for c in recent_claims if c["agent"] == agent_id]

    # 8. Recent conversation already in ADK session
    recent_messages = session.get_recent_messages(limit=10)

    # 9. Build the prompt
    return AgentContext(
        character=character,
        state=CurrentState(
            trust=trust,
            trust_history=format_trust_events(trust_events),
            story_phase=story_phase,
            key_accessed=key_status.access_count > 0,
            key_accesses_remaining=key_status.access_limit - key_status.access_count,
            milestones=milestones,
            # Immersion state
            lifecycle=lifecycle,
            tone_modifier=tone_modifier,
            world_exposure=exposure,
        ),
        knowledge=knowledge,
        inter_agent_knowledge=inter_agent_knowledge,
        memories=memories,
        conversation=recent_messages,
        new_message=new_message,
        instructions=get_generation_instructions(agent_id, story_phase, lifecycle),
        consistency_constraints=format_claim_constraints(agent_claims)
    )
```

---

## Message Processing Pipeline

### Full Flow (Player Sends Message)

```
┌─────────────────────────────────────────────────────────────────┐
│            MESSAGE PROCESSING PIPELINE (With Immersion)          │
└─────────────────────────────────────────────────────────────────┘

  PLAYER MESSAGE
       │
       ▼
┌──────────────────┐
│ 1. RECEIVE       │  Store metadata in DB (no content)
│    & ROUTE       │  Add to ADK session, identify target agent
└────────┬─────────┘  Check channel ownership for routing
         │
         ▼
┌──────────────────┐
│ 2. CLASSIFY      │  Gemini Flash (~100 tokens)
│    (Immediate)   │  Extract intent, sentiment, behaviors
└────────┬─────────┘  Detect lies, trust signals, revelations
         │            NEW: Detect exposure-triggering behaviors
         ▼
┌──────────────────┐
│ 3. UPDATE STATE  │  Apply trust changes, record knowledge
│                  │  NEW: Update exposure level
└────────┬─────────┘  NEW: Update engagement timestamps
         │            NEW: Check lifecycle transition triggers
         ▼
┌──────────────────┐
│ 4. CHECK         │  Is this a key moment?
│    SIGNIFICANCE  │  NEW: Did player introduce agents?
└────────┬─────────┘  NEW: Queue inter-agent exchange if triggered
         │
         ▼
┌──────────────────┐
│ 5. CHECK         │  NEW: Is agent lifecycle "gone"? → No response
│    LIFECYCLE     │  Is lifecycle "silent"? → Maybe respond (prob check)
└────────┬─────────┘  Apply response_delay_multiplier
         │
         ▼
┌──────────────────┐
│ 6. ASSEMBLE      │  Load character + state + knowledge
│    CONTEXT       │  + memories + recent conversation
└────────┬─────────┘  NEW: Include lifecycle, exposure, inter-agent knowledge
         │            NEW: Include consistency constraints from claims
         ▼
┌──────────────────┐
│ 7. GENERATE      │  Gemini Pro (quality response)
│    RESPONSE      │  Full agent context with immersion state
└────────┬─────────┘  NEW: Apply tone_modifier from lifecycle
         │
         ▼
┌──────────────────┐
│ 8. EXTRACT       │  NEW: Extract claims from agent response
│    CLAIMS        │  Check for contradictions via Memory Bank
└────────┬─────────┘  Store significant claims (PostgreSQL + Memory Bank)
         │
         ▼
┌──────────────────┐
│ 9. VALIDATE      │  Check for character breaks
│                  │  Check for impossible knowledge
└────────┬─────────┘  NEW: Check for claim contradictions
         │            Retry if needed
         ▼
┌──────────────────┐
│ 10. SCHEDULE     │  Calculate response delay
│     DELIVERY     │  NEW: Apply lifecycle delay_multiplier
└────────┬─────────┘  Queue for delivery
         │
         ▼
┌──────────────────┐
│ 11. DELIVER      │  Send via email/sms
│                  │  Store metadata in DB, content in session
└────────┬─────────┘  Update engagement timestamps
         │
         ▼
┌──────────────────┐
│ 12. SYNC         │  Add session to Memory Bank
│     & EVALUATE   │  NEW: Evaluate spawn conditions
└──────────────────┘  NEW: Process queued inter-agent exchanges
```

### Lifecycle Check (Step 5) Detail

```python
async def check_lifecycle_before_response(
    player_id: str,
    agent_id: str,
    session: Session
) -> ResponseDecision:
    """Determine if/how agent should respond based on lifecycle."""

    lifecycle = session.state.get(f"agent:{agent_id}:lifecycle", "engaged")
    response_prob = session.state.get(f"agent:{agent_id}:response_prob", 1.0)
    delay_mult = session.state.get(f"agent:{agent_id}:delay_mult", 1.0)
    tone = session.state.get(f"agent:{agent_id}:tone", "normal")

    if lifecycle == "gone":
        return ResponseDecision(should_respond=False)

    if lifecycle == "silent":
        # Probabilistic response
        if random.random() > response_prob:
            return ResponseDecision(should_respond=False)

    return ResponseDecision(
        should_respond=True,
        delay_multiplier=delay_mult,
        tone_modifier=tone
    )
```

### Inter-Agent Exchange Processing (Step 12) Detail

```python
async def process_queued_exchanges(player_id: str, session: Session):
    """Process any inter-agent exchanges triggered during this message."""

    queued = session.state.get("temp:queued_exchanges", [])

    for exchange_trigger in queued:
        from_agent = exchange_trigger["from"]
        to_agent = exchange_trigger["to"]
        trigger_type = exchange_trigger["type"]

        # Evaluate what gets shared (deterministic)
        exchange = await evaluate_sharing(from_agent, to_agent, player_id, trigger_type)

        # Store exchange record
        await db.insert_exchange(exchange)

        # Update session state with new awareness
        session.state[f"agent:{to_agent}:knows_about:{from_agent}"] = True
        session.state[f"agent:{to_agent}:learned_from:{from_agent}"] = exchange.knowledge_shared

    # Clear queue
    session.state["temp:queued_exchanges"] = []
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
    """Load ALL relevant state into ADK session at start."""

    # === CORE STATE ===
    ember_trust = await db.get_trust(player_id, 'ember')
    miro_trust = await db.get_trust(player_id, 'miro')
    phase = await calculate_story_phase(player_id)

    session.state["user:trust_ember"] = ember_trust.trust_score
    session.state["user:trust_miro"] = miro_trust.trust_score
    session.state["user:story_phase"] = phase
    session.state["user:engagement_level"] = calculate_engagement(player_id)

    # === IMMERSION STATE ===

    # Agent lifecycle (per agent)
    for agent_id in ['ember', 'miro']:
        lifecycle = await db.get_lifecycle(player_id, agent_id)
        if lifecycle:
            session.state[f"agent:{agent_id}:lifecycle"] = lifecycle.state
            session.state[f"agent:{agent_id}:response_prob"] = lifecycle.response_probability
            session.state[f"agent:{agent_id}:delay_mult"] = lifecycle.response_delay_multiplier
            session.state[f"agent:{agent_id}:tone"] = lifecycle.tone_modifier

    # World state
    world = await db.get_world_state(player_id)
    if world:
        session.state["world:exposure"] = world.exposure_level
        session.state["world:spawn_ready"] = world.spawn_conditions_met
        session.state["world:thursday_passed"] = world.thursday_passed

    # Inter-agent awareness
    exchanges = await db.get_agent_awareness(player_id)
    for ex in exchanges:
        session.state[f"agent:{ex.from_agent}:knows_about:{ex.to_agent}"] = True
        session.state[f"agent:{ex.from_agent}:learned_from:{ex.to_agent}"] = ex.knowledge_shared

    # Channel ownership
    for channel in ['email', 'sms']:
        owner = await db.get_channel_owner(player_id, channel)
        if owner:
            session.state[f"channel:{channel}:owner"] = owner.current_agent_id

    # Recent claims (hot cache for consistency checking)
    claims = await db.get_recent_claims(player_id, limit=10)
    session.state["cache:recent_claims"] = [
        {"agent": c.agent_id, "claim": c.claim, "is_true": c.is_true}
        for c in claims
    ]

    # Engagement state
    engagement = await db.get_engagement(player_id)
    if engagement:
        session.state["user:engagement_state"] = engagement.state
```

### After Each Exchange

```python
async def persist_state_changes(
    player_id: str,
    session: Session,
    classification: dict,
    agent_response: str | None = None
):
    """Write ADK state changes back to DB after each exchange."""

    # === CORE STATE ===

    # Apply trust changes
    for key, delta in classification["state_changes"].items():
        agent = key.replace("trust_", "")
        await db.update_trust(player_id, agent, delta, classification)

    # Record new knowledge
    for fact in classification["new_knowledge"]:
        await db.add_knowledge(player_id, fact, source_agent, message_id)

    # Key moments
    if classification["is_key_moment"]:
        await memory_service.add_session_to_memory(player_id, session)

    # === IMMERSION STATE ===

    # Update engagement timestamps
    await db.update_engagement_timestamp(player_id, direction="inbound")

    # Check for exposure-triggering behaviors
    for behavior, triggered in classification["behaviors"].items():
        if triggered and behavior in EXPOSURE_TRIGGERS:
            delta = EXPOSURE_TRIGGERS[behavior]
            await update_exposure(player_id, delta, behavior, session)

    # Check lifecycle transition triggers
    for agent_id in ['ember', 'miro']:
        await evaluate_lifecycle_transition(player_id, agent_id, session)

    # Check inter-agent exchange triggers
    if classification["behaviors"].get("shares_info_from_other"):
        await trigger_inter_agent_exchange(player_id, classification, session)


async def persist_agent_response(
    player_id: str,
    agent_id: str,
    agent_response: str,
    message_id: UUID,
    session: Session
):
    """Additional persistence after agent generates response."""

    # Extract and store claims from agent response
    claims = await classify_agent_claims(agent_response)

    for claim in claims:
        if claim.significance in ['high', 'critical']:
            # Check for contradictions
            similar = await memory_bank.search_memory(
                query=claim.statement,
                user_id=player_id,
                filters={"type": "claim", "agent_id": agent_id}
            )
            contradiction = detect_contradiction(claim, similar)

            # Store in PostgreSQL
            claim_id = await db.insert_claim(
                player_id=player_id,
                agent_id=agent_id,
                claim=claim.statement,
                claim_type=claim.type,
                is_true=evaluate_ground_truth(agent_id, claim),
                significance=claim.significance,
                message_id=message_id,
                contradicted_by=contradiction.id if contradiction else None
            )

            # Index in Memory Bank for future semantic search
            await memory_bank.add_memory(
                user_id=player_id,
                content=f"[{agent_id} claim] {claim.statement}",
                metadata={"claim_id": str(claim_id), "agent_id": agent_id, "type": "claim"}
            )

    # Update engagement timestamp for outbound
    await db.update_engagement_timestamp(player_id, direction="outbound")
```

---

## Immersion System Tables

> See [IMMERSION_DESIGN.md](IMMERSION_DESIGN.md) for full design context.

These tables support advanced gameplay mechanics. Each component uses a **hybrid storage strategy** across PostgreSQL, ADK Session, and Memory Bank based on access patterns.

### Storage Decision Matrix

| Component | PostgreSQL | ADK Session | Memory Bank | Access Pattern |
|-----------|------------|-------------|-------------|----------------|
| **Agent Claims** | Metadata, is_true | Last 10 claims (cache) | Claim text (semantic) | Read every response |
| **Agent Lifecycle** | Full record | State + modifiers | - | Read every response |
| **World State** | Source of truth | Exposure + spawn | - | Read every response |
| **Exposure Events** | Audit log | - | - | Write-heavy, rare read |
| **Inter-Agent Exchanges** | Full history | Awareness flags | - | Event-driven |
| **Player Engagement** | State + timestamps | Current state | - | Batch updates |
| **Channel Ownership** | Ownership record | Current owner | Scoped access | Per-message routing |

---

### Agent Claims (Consistency Tracking)

Tracks significant claims made by agents to prevent contradictions. Uses **hybrid storage** because contradiction detection requires semantic similarity search.

**PostgreSQL (Structured Metadata):**

```sql
CREATE TABLE agent_claims (
    id UUID PRIMARY KEY,
    player_id UUID REFERENCES players(id),
    agent_id TEXT NOT NULL,
    claim TEXT NOT NULL,
    claim_type TEXT NOT NULL,  -- 'action', 'fact', 'opinion', 'promise'
    is_true BOOLEAN NOT NULL,
    significance TEXT NOT NULL,  -- 'low', 'medium', 'high', 'critical'
    message_id UUID REFERENCES messages(id),
    contradicted_by UUID REFERENCES agent_claims(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_claims_player_agent
ON agent_claims(player_id, agent_id, significance);
```

**ADK Session (Hot Cache):**

```python
# Hydrated at session start, used for quick consistency checks
session.state["cache:recent_claims"] = [
    {"agent": "ember", "claim": "I deleted the email", "is_true": False},
    # ... last 10 claims
]
```

**Memory Bank (Semantic Search):**

Claims are also stored in Memory Bank with agent tagging for semantic contradiction detection:

```python
await memory_bank.add_memory(
    user_id=player_id,
    content=f"[{agent_id} claim] {claim.statement}",
    metadata={"claim_id": str(claim_id), "agent_id": agent_id, "type": "claim"}
)
```

**Ground Truth Mechanism:**

Ground truth is defined in agent YAML configs and evaluated during claim extraction:

```yaml
# In agent config (e.g., ember.md)
ground_truth:
  facts:
    - pattern: "I deleted the email"
      truth: false
    - pattern: "I can't see if you use the key"
      truth: false
    - pattern: "I made a typo"
      truth: true
  rules:
    - pattern: "I don't know *"
      evaluate: "check agent.knowledge.doesnt_know"
```

**Pipeline Integration (Step 6.5):**

Claims are extracted AFTER response generation, BEFORE validation:

```python
async def extract_and_store_claims(agent_response: str, agent_id: str, player_id: UUID):
    # 1. Extract claims via Gemini Flash
    claims = await classify_agent_claims(agent_response)

    for claim in claims:
        if claim.significance in ['high', 'critical']:
            # 2. Check for contradictions via Memory Bank semantic search
            similar = await memory_bank.search_memory(
                query=claim.statement,
                user_id=player_id,
                filters={"type": "claim", "agent_id": agent_id}
            )
            contradiction = detect_contradiction(claim, similar)

            # 3. Store in PostgreSQL
            await db.insert_claim(...)

            # 4. Index in Memory Bank
            await memory_bank.add_memory(...)
```

---

### Agent Lifecycle

Tracks agent state progression (engaged → cooling → silent → gone).

**PostgreSQL (Source of Truth):**

```sql
CREATE TABLE agent_lifecycle (
    player_id UUID REFERENCES players(id),
    agent_id TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'engaged',
    reason TEXT,
    transitioned_at TIMESTAMPTZ DEFAULT NOW(),
    response_probability FLOAT DEFAULT 1.0,
    response_delay_multiplier FLOAT DEFAULT 1.0,
    tone_modifier TEXT DEFAULT 'normal',
    PRIMARY KEY (player_id, agent_id)
);

-- Transition history for analytics
CREATE TABLE lifecycle_transitions (
    id UUID PRIMARY KEY,
    player_id UUID REFERENCES players(id),
    agent_id TEXT NOT NULL,
    from_state TEXT NOT NULL,
    to_state TEXT NOT NULL,
    reason TEXT,
    trust_at_transition INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**ADK Session (Hot Cache):**

```python
# Per-agent lifecycle state, hydrated at session start
session.state["agent:ember:lifecycle"] = "engaged"
session.state["agent:ember:response_prob"] = 1.0
session.state["agent:ember:delay_mult"] = 1.0
session.state["agent:ember:tone"] = "normal"
```

**Lifecycle ↔ Trust Relationship:**

Trust can trigger lifecycle transitions, but they are separate systems:

```yaml
lifecycle_rules:
  transitions:
    engaged_to_cooling:
      triggers:
        - trust_below: -50
        - goal_achieved: true
        - player_betrayal: true
      effects:
        response_probability: 0.7
        response_delay_multiplier: 2.0
        tone_modifier: "terse"

    cooling_to_silent:
      triggers:
        - days_in_state: 3
        - trust_below: -80
      effects:
        response_probability: 0.2
        response_delay_multiplier: 4.0
        tone_modifier: "cold"

    silent_to_gone:
      triggers:
        - days_in_state: 7
        - story_event: "agent_compromised"
      effects:
        response_probability: 0.0
```

---

### World State (Minimal MVP)

Per-player world simulation tracking exposure and spawn conditions.

**PostgreSQL (Source of Truth):**

```sql
CREATE TABLE world_state (
    player_id UUID PRIMARY KEY REFERENCES players(id),
    exposure_level INT DEFAULT 0 CHECK (exposure_level >= 0 AND exposure_level <= 100),
    spawn_conditions_met TEXT[] DEFAULT '{}',
    thursday_passed BOOLEAN DEFAULT FALSE,
    thursday_consequences_applied BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE exposure_events (
    id UUID PRIMARY KEY,
    player_id UUID REFERENCES players(id),
    delta INT NOT NULL,
    reason TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_exposure_events_player
ON exposure_events(player_id, created_at DESC);
```

**ADK Session (Hot Cache):**

```python
session.state["world:exposure"] = 35
session.state["world:spawn_ready"] = ["cipher"]
session.state["world:thursday_passed"] = False
```

**Exposure Triggers:**

Exposure changes are triggered by classification results and story events:

```python
EXPOSURE_TRIGGERS = {
    # Classification behaviors → delta
    "key_accessed": +30,
    "dashboard_accessed": +5,  # Capped at +15 total
    "forwarded_agent_message": +20,
    "mentioned_agent_to_other": +10,

    # Engagement patterns → delta
    "player_went_silent_7d": -10,
    "player_deleted_key": -20,

    # Story events → delta
    "ember_lifecycle_gone": +15,
    "miro_lifecycle_gone": +10,
}
```

**Spawn Condition Evaluation:**

Defined in agent configs, evaluated after each exposure change:

```yaml
# In new agent config
spawn:
  conditions:
    any:  # OR logic
      - exposure_gte: 50
      - agent_lifecycle: {ember: "gone"}
      - milestone: "player_mentioned_key_to_miro"
```

---

### Inter-Agent Exchanges

Tracks information sharing between agents when they become aware of each other.

**PostgreSQL (Exchange Record):**

```sql
CREATE TABLE inter_agent_exchanges (
    id UUID PRIMARY KEY,
    player_id UUID REFERENCES players(id),
    from_agent TEXT NOT NULL,
    to_agent TEXT NOT NULL,
    trigger TEXT NOT NULL,
    knowledge_shared TEXT[] NOT NULL,
    knowledge_withheld TEXT[] NOT NULL,
    trust_delta INT DEFAULT 0,
    alliance_level TEXT,
    surfaced_to_player BOOLEAN DEFAULT FALSE,
    surface_message_id UUID REFERENCES messages(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_exchanges_player
ON inter_agent_exchanges(player_id, created_at DESC);
```

**ADK Session (Awareness Flags):**

```python
session.state["agent:ember:knows_about:miro"] = True
session.state["agent:ember:learned_from:miro"] = ["player_is_investigating"]
```

**Sharing Evaluation Algorithm:**

Sharing is evaluated deterministically based on agent personality configs:

```yaml
# In agent config
sharing:
  default_stance: guarded  # or 'open', 'transactional'

  always_shares:
    - player_is_suspicious
    - player_behavior_warnings

  always_withholds:
    - own_involvement
    - monitoring_capability
    - player_trust_level

  trades_for:
    - network_information
    - player_cooperation_proof
```

**Exchange Triggers:**

```python
EXCHANGE_TRIGGERS = {
    "player_introduced_agents": {
        "detection": "classification.behaviors.shares_contact",
        "timing": "immediate"
    },
    "player_forwarded_message": {
        "detection": "classification.behaviors.shares_info_from_other",
        "timing": "immediate"
    },
    "both_agents_active_48h": {
        "detection": "scheduled_job",
        "timing": "daily_check"
    }
}
```

---

### Player Engagement

Tracks player activity for pacing and re-engagement.

**PostgreSQL (Source of Truth):**

```sql
CREATE TABLE player_engagement (
    player_id UUID PRIMARY KEY REFERENCES players(id),
    state TEXT NOT NULL DEFAULT 'active',
    last_player_message_at TIMESTAMPTZ,
    last_agent_message_at TIMESTAMPTZ,
    reengagement_attempts INT DEFAULT 0,
    last_reengagement_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**ADK Session:**

```python
session.state["user:engagement_state"] = "active"
```

**State Transitions (Scheduled Job):**

```python
# Runs hourly via Huey
async def update_engagement_states():
    # active → casual (3 days)
    await db.execute("""
        UPDATE player_engagement SET state = 'casual'
        WHERE state = 'active'
        AND last_player_message_at < NOW() - INTERVAL '3 days'
    """)

    # casual → dormant (7 days)
    # dormant → lapsed (14 days)
    # lapsed → churned (21 days)
```

---

### Channel Ownership

Tracks which agent owns each communication channel for routing and inheritance.

**PostgreSQL:**

```sql
CREATE TABLE channel_ownership (
    player_id UUID REFERENCES players(id),
    channel TEXT NOT NULL,
    current_agent_id TEXT NOT NULL,
    previous_agents TEXT[] DEFAULT '{}',
    inherited_at TIMESTAMPTZ,
    inheritance_type TEXT,  -- 'full_history', 'partial', 'none'
    PRIMARY KEY (player_id, channel)
);
```

**ADK Session:**

```python
session.state["channel:email:owner"] = "ember"
session.state["channel:sms:owner"] = "miro"
```

**Inheritance Types:**

| Type | New Agent Access |
|------|------------------|
| `full_history` | All prior messages via Memory Bank |
| `partial` | Message summaries only |
| `none` | Only messages since inheritance |

Inheritance type affects Memory Bank queries during context assembly:

```python
async def get_inherited_context(player_id, agent_id, channel):
    ownership = await db.get_channel_ownership(player_id, channel)

    if ownership.inheritance_type == 'none':
        return await memory_bank.search_memory(
            user_id=player_id,
            filters={"after": ownership.inherited_at}
        )
    elif ownership.inheritance_type == 'partial':
        return await memory_bank.search_memory(
            user_id=player_id,
            filters={"type": "summary"}
        )
    else:  # full_history
        return await memory_bank.search_memory(user_id=player_id)
```

---

## Summary

| Data Type | PostgreSQL | ADK Session | Memory Bank | Purpose |
|-----------|------------|-------------|-------------|---------|
| Player identity | ✓ | - | - | Registration, auth |
| Trust scores | ✓ | ✓ (cache) | - | Triggers + context |
| Trust events | ✓ | - | - | Audit trail |
| Player knowledge | ✓ | - | - | Context assembly |
| Milestones | ✓ | - | - | Trigger evaluation |
| Message metadata | ✓ | - | - | Tracking, delivery |
| Message content | - | - | ✓ | Semantic search |
| Classifications | ✓ | - | - | State changes |
| Recent context | - | ✓ | - | Working memory |
| Agent claims | ✓ (metadata) | ✓ (last 10) | ✓ (semantic) | Consistency |
| Agent lifecycle | ✓ | ✓ (state) | - | Response behavior |
| World state | ✓ | ✓ (exposure) | - | Spawn conditions |
| Exposure events | ✓ | - | - | Audit log |
| Inter-agent exchanges | ✓ | ✓ (awareness) | - | Information sharing |
| Player engagement | ✓ | ✓ (state) | - | Pacing |
| Channel ownership | ✓ | ✓ (owner) | Scoped queries | Message routing |
