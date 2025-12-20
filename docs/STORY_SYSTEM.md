# Story System Design

> **Related Documents:**
> - [DATA_ARCHITECTURE.md](DATA_ARCHITECTURE.md) - Detailed data structures, storage layers, and context assembly
> - [OPENING_WEEK_TIMELINE.md](OPENING_WEEK_TIMELINE.md) - Day-by-day timing and triggers
> - [TECHNOLOGY_CHOICES.md](TECHNOLOGY_CHOICES.md) - Tech stack and infrastructure

## Philosophy

The story is a **living world**, not a scripted narrative. We define the skeleton - characters, relationships, goals, and world rules - and the AI generates the actual experience. Players don't follow a plot; they exist in a world where things happen around them and their choices create ripples.

### Core Principles

1. **Skeleton + AI**: Authors define structure, AI generates content
2. **Ripple Effects**: Every player choice subtly influences future events
3. **Meaningful Consequences**: Mistakes matter but aren't game-ending
4. **Ongoing Experience**: No fixed endpoint, story evolves indefinitely
5. **Interconnected Threads**: Events in one storyline affect others

---

## Core Concepts

### World State

The **World State** is the single source of truth about what has happened and what is currently true. All agents read from this shared state to maintain consistency.

```yaml
world_state:
  facts:
    - "Meridian Research exists"
    - "Dr. Vance works at Meridian"
    - "There was an incident at Facility 7"

  events:
    - id: "facility_7_incident"
      happened: true
      timestamp: "2024-01-10T03:00:00Z"
      known_by: ["elena", "marcus"]  # Which agents know about this

  player_knowledge:
    # What the player has learned (agents won't re-explain)
    - "facility_7_exists"
    - "elena_is_researcher"
```

### Characters (Agents)

Each character is defined by their **personality**, **goals**, **knowledge**, and **relationships**.

```yaml
character:
  id: "elena"
  name: "Dr. Elena Vance"

  # Core personality (feeds into AI system prompt)
  personality:
    traits: ["analytical", "paranoid", "guilt-ridden"]
    speech_style: "formal, precise, avoids small talk"
    quirks: ["uses scientific metaphors", "apologizes often"]

  # What drives this character
  goals:
    primary: "Expose what happened at Facility 7"
    secondary: "Protect herself from the organization"
    hidden: "Absolve her guilt for her role in the incident"

  # What this character knows
  knowledge:
    knows:
      - "The truth about Facility 7"
      - "Who else was involved"
    doesnt_know:
      - "Who leaked the initial documents"
      - "That Marcus is still alive"

  # How they relate to other characters
  relationships:
    marcus:
      type: "former_colleague"
      current: "believes_dead"
      trust: 0  # Can't trust someone you think is dead
    director_chen:
      type: "former_boss"
      current: "fears"
      trust: -80

  # Communication patterns
  behavior:
    response_speed: "slow"  # Takes hours to respond
    active_hours: "late_night"  # Messages at odd hours
    channels: ["email", "telegram"]
    initiates: true  # Will reach out unprompted
```

### Story Threads

A **Thread** is an ongoing storyline. Multiple threads run simultaneously and can influence each other.

```yaml
thread:
  id: "facility_7_conspiracy"
  name: "The Facility 7 Conspiracy"

  # Characters involved in this thread
  characters: ["elena", "marcus", "director_chen"]

  # Current state of this thread for a player
  state: "investigation"  # discovery → investigation → confrontation → resolution

  # Key milestones (not linear, can happen in various orders)
  milestones:
    - id: "first_contact"
      description: "Elena reaches out to player"
      triggered_by: "onboarding_complete"

    - id: "document_leak"
      description: "Elena sends classified documents"
      triggered_by:
        player_trust: ">= 30"
        days_since_first_contact: ">= 2"

    - id: "marcus_appears"
      description: "Marcus makes contact, contradicts Elena"
      triggered_by:
        milestone: "document_leak"
        days_elapsed: ">= 1"

    - id: "player_chooses_side"
      description: "Player implicitly aligns with Elena or Marcus"
      triggered_by:
        condition: "player_trust_elena > player_trust_marcus OR player_trust_marcus > player_trust_elena"
        threshold: 20  # Difference must be significant

  # How this thread connects to others
  connections:
    - thread: "personal_mystery"
      trigger: "player discovers elena's secret"
      effect: "unlocks new dialogue options with elena"
```

### Events

**Events** are things that happen in the world. They can be triggered by player actions, time, or conditions.

```yaml
event:
  id: "midnight_warning"

  # When this event triggers
  trigger:
    type: "condition"
    conditions:
      - milestone: "document_leak"
      - player_read_documents: true
      - time_since_read: ">= 4 hours"

  # What happens
  action:
    agent: "unknown"  # New character introduction
    channel: "telegram"
    message_intent: "warn player they're being watched"
    urgency: "high"

  # Consequences of this event
  effects:
    - add_world_fact: "player_is_being_monitored"
    - unlock_thread: "surveillance_subplot"
    - increase_tension: 10
```

---

## Ripple Effect System

Player choices don't create branches - they create **ripples** that influence future events and character behaviors.

### How Ripples Work

```
Player Action → Interpreted by System → Updates State → Affects Future
```

**Example:**

1. Player receives conflicting info from Elena and Marcus
2. Player tells Elena they believe Marcus
3. System interprets: `player_trust_elena -= 15`, `player_trust_marcus += 10`
4. Elena's future messages become more desperate/defensive
5. Marcus becomes more confident, shares more
6. Director Chen (who's monitoring) notes player's alliance

### State Variables

```yaml
player_state:
  # Relationships (per character)
  relationships:
    elena:
      trust: 45        # -100 to 100
      knowledge: 30    # How much player knows about them
      interactions: 12 # Total message count
    marcus:
      trust: 60
      knowledge: 15
      interactions: 5

  # Thread progress
  threads:
    facility_7_conspiracy:
      engagement: "high"  # Based on response rate
      progress: 0.4       # 0 to 1
      alignment: "marcus" # Who player seems to trust more

  # Overall metrics
  meta:
    engagement_level: "active"  # active, casual, dormant
    play_style: "investigative" # investigative, emotional, skeptical
    risk_tolerance: "medium"    # Based on choices made
```

### Ripple Rules

Define how actions affect state:

```yaml
ripple_rules:
  # When player agrees with an agent
  - trigger: "player_agrees"
    effects:
      - target_agent.trust: "+10"
      - other_agents.trust: "-5 if relationship == rival"

  # When player ignores messages
  - trigger: "player_no_response"
    duration: "24 hours"
    effects:
      - agent.concern: "+20"
      - agent.behavior: "send_followup"

  # When player shares info between agents
  - trigger: "player_reveals_info"
    source_agent: "$source"
    target_agent: "$target"
    effects:
      - source.trust: "-15 if info was confidential"
      - target.trust: "+10"
      - world.add_fact: "$target knows $info"
```

---

## Timeline & Pacing

### Time-Based Events

Some events happen on a schedule regardless of player action:

```yaml
scheduled_events:
  - id: "weekly_report"
    agent: "elena"
    schedule: "every monday 9am player_timezone"
    condition: "thread.facility_7.active"
    intent: "share weekly findings, maintain contact"

  - id: "tension_escalation"
    schedule: "after 7 days of thread activity"
    effect: "increase stakes, introduce new threat"
```

### Player-Gated Events

Some events wait for player action:

```yaml
gated_events:
  - id: "trust_revelation"
    gate: "player_trust_elena >= 70"
    action: "elena reveals her role in the incident"

  - id: "confrontation"
    gate: "player explicitly accuses elena"
    action: "elena either confesses or deflects based on trust level"
```

### Pacing Adaptation

System adapts to player engagement:

```yaml
pacing_rules:
  # Player is very active
  high_engagement:
    message_frequency: "2-4 per day"
    event_spacing: "hours"
    introduce_new_content: "frequently"

  # Player checks in occasionally
  medium_engagement:
    message_frequency: "1-2 per day"
    event_spacing: "days"
    agents_reference_time_gaps: true

  # Player is barely responding
  low_engagement:
    message_frequency: "every 2-3 days"
    content: "re-engagement attempts"
    agents_express_concern: true
    pause_major_events: true
```

---

## Content Authoring

### What Authors Define

| Element | Author Responsibility | AI Responsibility |
|---------|----------------------|-------------------|
| Characters | Personality, goals, relationships | Actual dialogue |
| World | Facts, setting, rules | Maintaining consistency |
| Milestones | Key story beats | When/how they occur |
| Threads | Structure, connections | Pacing, transitions |
| Events | Triggers, intents | Message content |

### Example: Minimal Story Definition

```yaml
# story/conspiracy_thriller.yaml

world:
  setting: "Modern day, tech industry"
  tone: "paranoid thriller"
  facts:
    - "MegaCorp is hiding something"
    - "People have disappeared"
    - "Player was chosen for a reason"

characters:
  - id: whistleblower
    role: "desperate insider"
    goal: "expose the truth"
    personality: "paranoid, cryptic, means well"

  - id: handler
    role: "mysterious ally"
    goal: "guide player, unclear motives"
    personality: "calm, professional, evasive"

  - id: hunter
    role: "corporate fixer"
    goal: "silence threats"
    personality: "polite, menacing, patient"

threads:
  - id: main
    starts_with: "whistleblower contacts player"
    escalates_to: "player must choose who to trust"

relationships:
  whistleblower_handler: "uneasy alliance"
  whistleblower_hunter: "mortal enemies"
  handler_hunter: "unknown to each other"
```

From this skeleton, the AI generates all actual content.

---

## AI Generation Guidelines

### System Prompt Structure

Each agent gets a system prompt built from:

```
1. Character definition (personality, goals, speech style)
2. Current world state (what's happened, what's true)
3. Relationship with player (trust, history, knowledge)
4. Current thread context (where we are in the story)
5. Recent conversation history
6. Generation guidelines (tone, length, style)
```

### Generation Rules

```yaml
generation_rules:
  # Content rules
  - "Never break character"
  - "Reference past conversations naturally"
  - "Don't repeat information player already knows"
  - "Match the urgency level to current story state"

  # Style rules
  - "Keep messages realistic length (not walls of text)"
  - "Use character's defined speech patterns"
  - "Include occasional typos for informal characters"

  # Narrative rules
  - "Don't resolve mysteries too quickly"
  - "Plant seeds for future reveals"
  - "React to player theories (incorporate or deflect)"
```

### Consistency Enforcement

```yaml
consistency:
  # Before generating, check:
  - "Does this contradict established world facts?"
  - "Does this reveal information the character doesn't know?"
  - "Does this match the character's current emotional state?"
  - "Does this fit the current pacing/tension level?"

  # After generating, validate:
  - "No meta-references (AI, game, etc.)"
  - "No impossible knowledge"
  - "Emotional consistency with recent events"
```

---

## Decisions

### Handling Players "Breaking" the Story

**Decision: Adapt to it**

When players go off-script or try to break immersion, agents incorporate it into the narrative:

```yaml
breaking_behavior_rules:
  # Player claims to know it's a game/AI
  - trigger: "player_meta_reference"
    response: "Agent expresses concern about player's mental state"
    effect: "Add 'player_acting_strange' to world state"
    example: "'You're talking nonsense. Are you okay? Has someone gotten to you?'"

  # Player goes completely off-topic
  - trigger: "player_off_script"
    response: "Agent is confused but tries to refocus"
    effect: "Note player unpredictability in their profile"
    example: "'I... don't know what you mean. Look, we don't have time for this.'"

  # Player tries to expose/confront the fiction
  - trigger: "player_confrontational"
    response: "Agent interprets it within the story world"
    effect: "Could trigger paranoia or concern from agents"
    example: "'You think this is some kind of game? People have DIED.'"
```

This keeps immersion intact while making player behavior part of the story. Agents might start questioning if the player is "compromised" or "testing them."

---

## Future Considerations (Post-MVP)

1. **Fresh content for ongoing play**
   - Modular story packs that plug into existing world
   - AI-generated expansion of threads
   - Seasonal events affecting all players

2. **Multiplayer / Shared world**
   - Shared lore vs fully isolated universes
   - Cross-player ripple effects
   - Collaborative discoveries

---

## Next Steps

1. ~~Design the 5 MVP characters with full configs~~ → See `/docs/story/agents/` (Ember & Miro complete)
2. ~~Define the initial story skeleton (threads, milestones)~~ → See [OPENING_WEEK_TIMELINE.md](OPENING_WEEK_TIMELINE.md)
3. Create the AI prompt templates → During implementation
4. Define the state machine for thread progression → During implementation

## Implementation Notes

The conceptual YAML structures in this document serve as design reference. For actual implementation details:

- **Data storage**: See [DATA_ARCHITECTURE.md](DATA_ARCHITECTURE.md)
- **Database schema**: See DATA_ARCHITECTURE.md § Database Schema
- **Context assembly**: See DATA_ARCHITECTURE.md § Context Assembly Pipeline
- **Token budgets**: See DATA_ARCHITECTURE.md § Token Budget
