# Immersion Design

> **Related Documents:**
> - [STORY_SYSTEM.md](STORY_SYSTEM.md) - Core story system philosophy and mechanics
> - [DATA_ARCHITECTURE.md](DATA_ARCHITECTURE.md) - Data structures and storage layers
> - [OPENING_WEEK_TIMELINE.md](OPENING_WEEK_TIMELINE.md) - Day-by-day timing and triggers

This document details the advanced mechanics that create deep player immersion in Argent. These systems work together to make players feel they've stumbled into something real.

---

## Design Principles

### Character Logic Over Plot Logic

Agents don't follow plot beats—they pursue **goals** against a player who has genuine agency. The "story" emerges from this collision.

**An agent isn't a narrator. An agent is a person who needs something.**

| Element | Description | Example |
|---------|-------------|---------|
| **Goal** | What they need from the player | Ember needs the player to ignore the key |
| **Stakes** | What happens if they fail | Ember faces exposure |
| **Fears** | What they're protecting against | Being discovered |
| **Emotional State** | Current disposition (shifts over time) | Anxious, manipulative, desperate |
| **Model of Player** | What they believe player knows/wants | "Player seems curious but cautious" |

When a player goes off-topic, agents don't "steer back to the plot." They react as their character would:
- A desperate character gets frustrated
- A manipulative character humors briefly, then redirects
- A patient character files it away for later leverage

### Gated Goals: Balancing Emergence with Story Beats

Agents pursue goals freely, but certain story beats are **gated** by conditions. When gate conditions are met, the beat must surface in the next response.

```yaml
# Agent definition enhancement
goals:
  primary:
    description: "Regain control of the key situation"
    behaviors: ["pressure to delete", "monitor usage", "deflect questions"]

  story_gates:
    - beat: "reveal_monitoring_capability"
      gate: "trust >= 40 OR player_used_key"
      behavior: "Ember admits she can see key usage"

    - beat: "breakdown_moment"
      gate: "trust <= -30 OR days_since_start >= 5"
      behavior: "Ember becomes desperate, reveals more than intended"

    - beat: "true_identity_hint"
      gate: "trust >= 70 AND player_asked_directly"
      behavior: "Ember slips, hints at who she really is"
```

This ensures key story beats happen while maintaining emergent behavior.

---

## Consistency Tracking

### The Consistency Problem

With agents giving conflicting information by design, we must track:
- **Claims made**: Agents must not contradict their own lies
- **Player reveals**: Agent A shouldn't know what player only told Agent B
- **Ground truth**: System knows reality to manage contradictions

**If Ember contradicts her own earlier lie, immersion shatters.**

### Agent Claims System

Track agent claims in a dedicated table (not mixed with player knowledge):

```yaml
agent_claim:
  player_id: UUID
  agent_id: "ember"
  claim: "I deleted the email on my end"
  claim_type: "action"  # action, fact, opinion, promise
  is_true: false        # Ground truth
  significance: "high"  # low, medium, high, critical
  message_id: UUID
  contradicted_by: null # Filled if later contradicted
```

### What Gets Tracked

| Claim Type | Example | Track? |
|------------|---------|--------|
| Lies about facts | "I deleted it" (didn't) | **Yes - critical** |
| Promises | "I won't share this" | **Yes - high** |
| Opinions | "I think Miro is dangerous" | **Yes - medium** |
| Small talk | "It's been a long day" | No |
| Deflections | "Let's not talk about that" | No |

### Classification Enhancement

The message classification system extracts claims from agent responses:

```yaml
agent_response_classification:
  claims_made:
    - statement: "I've never met him"
      claim_type: "fact"
      is_lie: true
      significance: "high"

  consistency_check:
    contradicts_previous: false
    previous_claim_id: null
```

---

## Character Lifecycle

Characters are mortal. An agent who no longer has a reason to contact you... doesn't.

### Lifecycle States

| State | Behavior | Player Experience |
|-------|----------|-------------------|
| **Engaged** | Actively pursuing goal, responsive | Regular contact, clear agenda |
| **Cooling** | Goal resolved or blocked, winding down | Shorter messages, longer delays |
| **Silent** | No longer initiating contact | May or may not reply if contacted |
| **Gone** | Will not reply | Disappeared, moved on, or dead |

**Critical rule: The player never receives explicit confirmation of which state a character is in.** They experience silence and wonder.

### Transition Signals

Agents always provide a signal before going silent (so it doesn't feel like a bug):

| Transition | Signal Example |
|------------|----------------|
| Engaged → Cooling | "I need some time to think. I'll be in touch." |
| Cooling → Silent | "I can't keep doing this. Please don't contact me." |
| Silent → Gone | No message—they just stop responding |

The final "silent → gone" transition has no message, creating intentional ambiguity.

### Lifecycle Triggers

```yaml
lifecycle_transitions:
  to_cooling:
    - goal_achieved: "Agent got what they wanted"
    - goal_failed: "Agent realizes player won't cooperate"
    - trust_threshold: "trust <= -50"
    - player_betrayal: "Player shared confidential info"

  to_silent:
    - days_in_cooling: ">= 3"
    - explicit_goodbye: "Agent said they need space"

  to_gone:
    - days_in_silent: ">= 7"
    - story_event: "Agent was compromised/caught"
    - player_action: "Player caused their exposure"
```

### Behavioral Modifiers

```yaml
lifecycle_behavior:
  engaged:
    response_probability: 1.0
    response_delay_hours: 1-4
    message_length: normal
    tone: normal

  cooling:
    response_probability: 0.8
    response_delay_hours: 8-24
    message_length: short
    tone: terse

  silent:
    response_probability: 0.2
    response_delay_hours: 24-72
    message_length: minimal
    tone: cold

  gone:
    response_probability: 0.0
```

---

## Channel Inheritance

When a character dies or disappears, their communication channel persists. A new character can inherit it.

**Same number. Different voice.**

### Why This Is Powerful

The contact in your phone has history. You see old messages. Intimate exchanges. And suddenly—the voice changes.

This creates layers of paranoia:
- Is this really a new person, or is the original character testing me?
- Did they kill the previous character, or is this them under duress?
- If they read the message history, they know what I revealed...

### Inheritance Signaling

**First occurrence: Explicit announcement** (establishes the mechanic exists)

```
"This isn't [previous name]. I found this device.
I've seen your conversation history. We should talk."
```

**Subsequent occurrences**: May be more gradual, since players now expect it.

### Knowledge Inheritance

```yaml
channel_inheritance:
  type: "full_history"  # full_history, partial, none

  new_agent_access:
    has:
      - previous_message_history
      - contacts_list
      - any_files_shared
    does_not_have:
      - things_discussed_in_person (referenced but not typed)
      - emotional_context
      - passwords_mentioned_verbally
```

### Player Testing

Players will test new contacts by referencing things only the original would know:

```yaml
# In inherited agent definition
behavior:
  when_tested:
    if_has_access: "respond correctly"
    if_no_access: "deflect or admit ignorance"

  examples:
    player: "What did I tell you about my sister?"
    # If new agent read history: accurate reference
    # If not: "I don't know what you mean. We haven't discussed that."
```

---

## World Layer

A per-player world simulation tracks the player's "footprint" independent of any active character.

### MVP Scope: Minimal World Layer

For MVP, track only:
- **Exposure level** (single integer)
- **Spawn conditions** (for new characters)

```yaml
world_state:
  player_id: UUID

  exposure_level: 35  # 0-100

  spawn_conditions_met:
    - "high_exposure"
    - "contacted_both_agents"
```

### Exposure Mechanics

| Action | Exposure Delta |
|--------|----------------|
| Use the key | +30 |
| Access dashboard 3+ times | +15 |
| Forward agent emails | +20 |
| Mention one agent to another | +10 |
| Go silent for 7+ days | -10 |
| Delete key (if Ember's goal achieved) | -20 |

### Character Spawning

New characters don't arrive because "the plot needs them." They arrive because the player's actions made them findable.

```yaml
# In new character definition
spawn:
  conditions:
    - exposure_level: ">= 50"
    - OR: "player_mentioned_key_to_miro"
    - OR: "ember_lifecycle == gone"

  introduction:
    trigger: "exposure_level >= 50"
    channel: "sms"
    first_message: "I've been watching the chatter. Your name keeps coming up."
```

### Future Expansion (Post-MVP)

```yaml
# More complex world layer for later
world_state:
  exposure_level: 35

  heat_sources:
    corporate_security: 30
    underground_network: 50
    government: 0

  deadlines:
    - id: "thursday"
      at: "2024-01-18T00:00:00Z"
      passed: false
      consequences: "soft"  # soft or hard

  scheduled_events:
    - trigger_at: "2024-01-20T09:00:00Z"
      event_type: "dead_drop"
      description: "Scheduled email from potentially dead character"
```

---

## Inter-Agent Communication

Characters exist beyond the player. They'd talk to each other, share information, scheme, betray.

### Player-Initiated Introductions

When a player introduces agents to each other:
- Player gives Miro Ember's contact info
- Player forwards a message from one to another
- Player tells Agent A something that reveals Agent B's existence

**Once two agents are aware of each other, the player loses control of information flow.**

### Sharing Logic (Deterministic)

Agents don't share everything. Each piece of information is evaluated:

```yaml
sharing_evaluation:
  factors:
    - goal: "Does sharing help my goal?"
    - trust: "How much do I trust this agent?"
    - leverage: "Does this give me power or give it away?"
    - personality: "Am I naturally guarded? A gossip?"
    - trade_value: "What do I get in return?"

  result: "share | withhold | trade | weaponize"
```

### Agent-Specific Sharing Rules

```yaml
ember:
  default_stance: guarded

  always_shares:
    - information_that_makes_player_look_bad
    - warnings_about_player_behavior

  always_withholds:
    - own_involvement_in_cover_up
    - player_trust_level
    - monitoring_capability

  trades_for:
    - information_about_miro's_network
    - proof_player_is_cooperating

miro:
  default_stance: transactional

  always_shares:
    - general_information_about_the_situation
    - player_questions (if interesting)

  always_withholds:
    - own_network_details
    - real_identity

  trades_for:
    - inside_access
    - exclusive_information
```

### Exchange Results

Inter-agent exchanges can remain invisible OR surface subtly:

**Invisible exchanges** (player never directly sees):
- Trust levels between agents shift
- Agents gain knowledge they shouldn't have from player
- Sets up future "slips" or reveals

**Surface via behavioral changes**:
- Tone shifts without explanation
- Agent references something player didn't tell them
- Agent becomes more guarded or more confident

```yaml
exchange:
  trigger: "player_gave_miro_ember_contact"

  miro_shares:
    - "player_is_actively_investigating"

  miro_withholds:
    - "own_agenda_with_player"

  ember_learns:
    - "miro_is_in_contact_with_player"

  surface_to_player:
    agent: "ember"
    delay_hours: 24
    message_hint: "I hear you're still looking into this."
    # Player realizes: How does she know? I told her I deleted it.
```

### Trust Levels Between Agents

| Level | Behavior |
|-------|----------|
| **Allied** | Share relevant info, coordinate—but still protect core secrets |
| **Transactional** | Trade information, always evaluate the deal |
| **Suspicious** | Withhold by default, test with low-value info |
| **Hostile** | Actively mislead, leak harmful info to third parties |

### The "Caught in a Lie" Moment

When agents compare notes and discover player contradictions:

```yaml
contradiction_discovered:
  ember_told: "Player said they deleted the key"
  miro_told: "Player said they're going to use the key"

  possible_reactions:
    confrontational:
      agent: "ember"
      message: "Interesting. Miro told me something very different."

    manipulative:
      agent: "miro"
      action: "says nothing, trust silently drops"

    strategic:
      agent: "ember"
      action: "files it away, uses as leverage later"
```

---

## Player Engagement States

### State Definitions

| State | Condition | Agent Behavior |
|-------|-----------|----------------|
| **Active** | Responded within 48 hours | Normal pacing |
| **Casual** | 3-5 days since response | Reduced frequency, concerned messages |
| **Dormant** | 7-13 days since response | Re-engagement hooks |
| **Lapsed** | 14-20 days since response | Weekly high-value only |
| **Churned** | 21+ days since response | Pause all messages |

### Re-Engagement Messaging

```yaml
reengagement:
  casual:
    message_type: "concerned check-in"
    example: "Is everything okay? I haven't heard from you."
    in_character: true

  dormant:
    message_type: "story hook"
    example: "Something's happened. I need to tell you."
    in_character: true

  lapsed:
    message_type: "major development"
    example: "[Significant story reveal or cliffhanger]"
    in_character: true
```

### Returning After Churn

When a player returns after 21+ days:

1. **World has moved on**
   - Some deadlines passed (with soft consequences)
   - Some agents may have changed lifecycle state
   - New spawn conditions may have been met

2. **First message acknowledges gap**
   ```
   Miro: "I thought they got to you. It's been weeks."
   ```

3. **Optional dashboard summary**
   - "Catch me up" option available
   - Not forced—player can discover organically

### No "Game Over" State

The game never ends. A churned player who returns finds:
- A world that evolved without them
- Agents in different states than before
- New opportunities, not punishment

This is thematic: the conspiracy continues whether you're watching or not.

---

## Pacing Constraints

### Cognitive Load Limits

Research-backed limits to prevent player overwhelm:

| Metric | Limit | Reasoning |
|--------|-------|-----------|
| Active characters | 2-4 max | Players can track 6-8 NPCs, but only 4 "hot" at once |
| Info per message | 3-4 items | Working memory constraint |
| Active plot threads | 2-3 | Beyond this, earlier threads forgotten |
| Messages per day | 4-6 total | Prevents notification fatigue |

### Character Introduction Pacing

```yaml
character_pacing:
  week_1: 2 characters (Ember, Miro)
  week_2: "+1-2 if conditions met"
  ongoing: "rotate prominence—some fade while new emerge"

  rule: "never more than 4 actively messaging at once"
```

### Message Frequency by Engagement

| Player Activity | Messages/Day | Agents Active |
|-----------------|--------------|---------------|
| High (daily) | 4-6 total | 2-3 |
| Medium (every 2-3 days) | 2-3 total | 1-2 |
| Low (weekly) | 1 total | 1 |

### Overwhelm Detection

```yaml
overwhelm_detection:
  signals:
    - unanswered_messages: ">= 3"
    - average_response_length: "decreasing"
    - response_time: "increasing"

  response:
    - reduce_message_frequency
    - consolidate_to_primary_agent
    - pause_new_character_introductions
```

---

## Deadline Mechanics

### The Thursday Deadline

The key email mentions "use before Thursday." This creates tension without hard failure.

**Soft consequences** (chosen design):

```yaml
thursday_deadline:
  passed: true

  consequences:
    ember:
      behavior: "more desperate, fewer options"
      trust_modifier: -10
      new_dialogue: "It's too late for the easy way."

    miro:
      behavior: "shifts approach"
      new_information: "reveals the deadline was artificial"

    world:
      exposure_delta: +20
      new_spawn_condition: "deadline_passed"
```

The game continues, but the landscape has shifted.

---

## Success Signals

How we know immersion is working:

| Signal | What It Indicates |
|--------|-------------------|
| **Reply depth** | Player writes substantive responses |
| **Unprompted contact** | Player initiates without being messaged |
| **Testing behavior** | Player tries to verify agent claims |
| **Emotional language** | Player expresses frustration, excitement, suspicion |
| **Cross-agent references** | Player mentions one agent to another |
| **Leak suspicion** | Player questions how an agent knew something |
| **Return after silence** | Player re-engages after going quiet |

---

## Implementation Checklist

### New Data Models Required

1. **AgentClaim** - Track agent statements for consistency
2. **AgentLifecycle** - Track lifecycle state per player-agent
3. **WorldState** - Per-player world simulation
4. **InterAgentExchange** - Track agent-to-agent information sharing
5. **PlayerEngagement** - Track engagement state and re-engagement attempts

### Classification Enhancements

1. Extract claims from agent responses (not just player messages)
2. Check for contradictions with previous claims
3. Evaluate significance of each claim

### Agent Behavior Additions

1. Lifecycle-aware response generation
2. Gate evaluation before response
3. Sharing evaluation when agents become aware of each other
4. Engagement-based pacing

### World Layer Integration

1. Exposure tracking on player actions
2. Spawn condition evaluation
3. Deadline tracking with soft consequences

---

*This document represents design decisions made in December 2024. Implementation will be iterative, with MVP focusing on lifecycle, claims tracking, and minimal world layer.*
