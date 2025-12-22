# Development Roadmap

A prioritized roadmap for ARGent development. Features are grouped by milestone and ordered by dependency.

---

## Milestone 1: Core Gameplay Loop (MVP)
*Goal: A complete player experience from registration to multi-day engagement*

### 1.1 Complete Agent Response Pipeline
The current pipeline generates responses but doesn't extract state changes.

- [ ] **Trust extraction from responses**
  - Classify agent responses for trust-relevant content
  - Update trust scores based on player agreement/disagreement
  - Log trust events with reasons
  - *Files: `src/agents/`, `src/services/`*

- [ ] **Knowledge extraction**
  - Extract facts revealed in conversations
  - Store in `player_knowledge` table
  - Inject known facts into agent prompts (avoid repetition)
  - *Files: `src/agents/prompt_builder.py`, `src/models/`*

- [ ] **Response classification**
  - Classify player messages for intent, sentiment, topics
  - Store classification results
  - Use for trust calculation and trigger evaluation
  - *Files: `src/services/classification.py` (new)*

### 1.2 Evidence Dashboard
The in-fiction page where players use their key.

- [ ] **Dashboard page**
  - Create `/evidence` route with key input form
  - Corporate intranet styling (dated, internal feel)
  - Key validation against `player_keys` table
  - *Files: `src/api/evidence.py` (new), `templates/evidence/`*

- [ ] **Access logging**
  - Log every access attempt (success/failure)
  - Track access count against limit (3-5 uses)
  - Emit `key_used` event for story triggers
  - *Files: `src/models/player.py`, `src/services/`*

- [ ] **Dashboard content**
  - 2-3 internal logs/memos
  - 1 redacted document
  - 1 email thread fragment
  - *Files: `templates/evidence/`, static content*

- [ ] **Ember visibility**
  - Ember's prompt includes key access status
  - Triggers trust break if player lied about not using it
  - *Files: `src/agents/ember/`*

### 1.3 Condition-Based Triggers
Currently only time-based triggers. Need condition evaluation.

- [ ] **Trigger evaluator**
  - Evaluate conditions: trust thresholds, milestones, days elapsed
  - Support compound conditions (AND/OR)
  - *Files: `src/scheduler/evaluator.py` (new)*

- [ ] **Dashboard reveal trigger**
  - Fire when: day >= 3 AND trust > 40 with any agent
  - Higher-trust agent reveals access
  - *Files: `src/scheduler/events.py`*

- [ ] **Post-Thursday triggers**
  - Detect when Thursday deadline passes
  - Shift agent behavior (Ember desperate, Miro strategic)
  - *Files: `src/scheduler/events.py`*

---

## Milestone 2: Immersion Systems
*Goal: Agents feel like real people with consistent behavior*

### 2.1 Agent Consistency (Claims Tracking)
Prevent agents from contradicting themselves.

- [ ] **Claims extraction**
  - Extract significant claims from agent responses
  - Categorize: action, fact, opinion, promise
  - Mark ground truth (is this claim true?)
  - *Files: `src/services/claims.py` (new)*

- [ ] **Claims storage**
  - `agent_claims` table with player_id, agent_id, claim, is_true
  - Index recent claims for prompt injection
  - *Files: `src/models/claims.py` (new)*

- [ ] **Consistency constraints**
  - Inject recent claims into agent prompts
  - "Do not contradict: [list of previous claims]"
  - *Files: `src/agents/prompt_builder.py`*

### 2.2 Agent Lifecycle
Characters can fade, go silent, or disappear.

- [ ] **Lifecycle state model**
  - States: engaged, cooling, silent, gone
  - Store per player-agent pair
  - *Files: `src/models/lifecycle.py` (new)*

- [ ] **Lifecycle transitions**
  - Define triggers: trust thresholds, goal achieved, days elapsed
  - Transition signals (agents warn before going silent)
  - *Files: `src/services/lifecycle.py` (new)*

- [ ] **Behavioral modifiers**
  - Response probability per state (1.0 → 0.8 → 0.2 → 0)
  - Response delay multiplier
  - Tone modifier (normal → terse → cold)
  - *Files: `src/agents/base.py`*

### 2.3 Player Engagement Tracking
Adapt pacing to player activity.

- [ ] **Engagement state model**
  - States: active, casual, dormant, lapsed, churned
  - Track last message timestamps
  - *Files: `src/models/engagement.py` (new)*

- [ ] **State transitions**
  - Scheduled job to update states based on inactivity
  - active (< 48h) → casual (3-5d) → dormant (7-13d) → lapsed (14-20d) → churned (21d+)
  - *Files: `src/scheduler/jobs.py`*

- [ ] **Re-engagement messaging**
  - Concerned check-ins for casual players
  - Story hooks for dormant players
  - *Files: `src/scheduler/events.py`*

---

## Milestone 3: Multi-Agent Orchestration
*Goal: Agents aware of each other, coordinated storytelling*

### 3.1 Inter-Agent Awareness
Agents learn about each other through player actions.

- [ ] **Introduction detection**
  - Detect when player mentions one agent to another
  - Detect when player forwards messages
  - *Files: `src/services/classification.py`*

- [ ] **Awareness state**
  - Track which agents know about each other per player
  - Store in `inter_agent_exchanges` table
  - *Files: `src/models/exchanges.py` (new)*

- [ ] **Knowledge sharing evaluation**
  - Per-agent sharing rules (always share, always withhold, trade)
  - Deterministic evaluation based on personality
  - *Files: `src/services/sharing.py` (new)*

### 3.2 Coordinated Messaging
Prevent message overlap, ensure coherent pacing.

- [ ] **Message queue coordination**
  - Maximum messages per day per player
  - Minimum gap between different agents
  - *Files: `src/scheduler/coordinator.py` (new)*

- [ ] **Conflict detection**
  - Don't send conflicting info at the same time
  - Space out reveals
  - *Files: `src/scheduler/coordinator.py`*

### 3.3 Additional Agents
Expand the cast based on story progression.

- [ ] **Cipher agent**
  - The intended recipient
  - Cold, technical personality
  - Spawn condition: exposure >= 50 OR Ember mentions them
  - *Files: `src/agents/cipher/` (new)*

- [ ] **Kessler agent**
  - Corporate fixer
  - Polite, professional, unsettling
  - Spawn condition: high exposure OR player causes visibility
  - *Files: `src/agents/kessler/` (new)*

---

## Milestone 4: World Simulation
*Goal: Per-player world state that evolves*

### 4.1 Exposure System
Track how "visible" the player has become.

- [ ] **Exposure tracking**
  - Exposure level 0-100 per player
  - Events that increase/decrease exposure
  - *Files: `src/models/world.py` (new)*

- [ ] **Exposure triggers**
  - Key used: +30
  - Dashboard accessed 3+ times: +15
  - Forwarded agent message: +20
  - Player went silent 7d: -10
  - *Files: `src/services/exposure.py` (new)*

### 4.2 Character Spawning
New characters appear based on player actions.

- [ ] **Spawn condition evaluation**
  - Check conditions after exposure changes
  - Support: exposure threshold, agent lifecycle state, milestones
  - *Files: `src/scheduler/spawning.py` (new)*

- [ ] **Spawn messaging**
  - First contact for new agents
  - Contextual introduction based on trigger
  - *Files: `src/scheduler/events.py`*

### 4.3 Deadline Consequences
Thursday deadline has soft consequences.

- [ ] **Thursday tracking**
  - Track when 4 days have passed since game start
  - Flag `thursday_passed` in world state
  - *Files: `src/models/world.py`*

- [ ] **Post-Thursday behavior**
  - Ember: more desperate, fewer options
  - Miro: reveals deadline was artificial
  - Exposure +20
  - *Files: `src/agents/*/persona.py`*

---

## Milestone 5: Long-Term Memory
*Goal: Semantic search over conversation history*

### 5.1 Memory Bank Integration
Connect to Vertex AI Memory Bank (or alternative).

- [ ] **Memory service**
  - Store conversation content in Memory Bank
  - Per-player isolation
  - *Files: `src/services/memory.py` (new)*

- [ ] **Session sync**
  - Save sessions to Memory Bank after key moments
  - Index claims and significant events
  - *Files: `src/agents/base.py`*

### 5.2 Semantic Retrieval
Pull relevant context from past conversations.

- [ ] **Memory search**
  - Query Memory Bank for relevant past interactions
  - Filter by agent, topic, significance
  - *Files: `src/services/memory.py`*

- [ ] **Context assembly**
  - Include relevant memories in agent prompts
  - Budget: ~400 tokens for memories
  - *Files: `src/agents/prompt_builder.py`*

---

## Milestone 6: Channel Inheritance
*Goal: New characters can take over channels*

- [ ] **Channel ownership model**
  - Track current owner per channel per player
  - Store previous owners and inheritance type
  - *Files: `src/models/channels.py` (new)*

- [ ] **Inheritance mechanics**
  - Full history, partial (summaries only), or none
  - Affects what new agent can reference
  - *Files: `src/services/inheritance.py` (new)*

- [ ] **Takeover messaging**
  - First occurrence: explicit announcement
  - "This isn't [previous]. I found this device."
  - *Files: `src/scheduler/events.py`*

---

## Backlog (Future Considerations)

### Quality of Life
- [ ] Player dashboard for tracking story progress
- [ ] "Catch me up" summary after long absence
- [ ] Quiet hours configuration
- [ ] Timezone-aware scheduling

### Content Expansion
- [ ] Additional story threads beyond the key
- [ ] Modular story packs
- [ ] Seasonal events

### Multiplayer
- [ ] Shared world state across players
- [ ] Cross-player ripple effects
- [ ] Collaborative discoveries

### Voice Channel
- [ ] Voicemail drops from agents
- [ ] Voice synthesis for agent calls
- [ ] Speech-to-text for player responses

---

## How to Use This Roadmap

1. **Pick a milestone** — Work through milestones in order; they build on each other
2. **Check dependencies** — Some features require others (e.g., triggers need classification)
3. **Mark complete** — Check off items as they're implemented
4. **Update as needed** — This is a living document; adjust based on learnings

### Priority Guidelines

- **Milestone 1** is required for a playable MVP
- **Milestone 2** makes agents feel real
- **Milestone 3** enables the multi-agent experience
- **Milestones 4-6** add depth but aren't blocking
