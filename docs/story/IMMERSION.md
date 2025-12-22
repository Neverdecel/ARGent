# Immersion Design

> **For implementation details, see the code.** This document describes design principles for deep player immersion.

---

## Core Principle: Character Logic Over Plot Logic

Agents don't follow plot beats - they pursue **goals** against a player who has genuine agency. The "story" emerges from this collision.

**An agent isn't a narrator. An agent is a person who needs something.**

| Element | What It Is | Example |
|---------|------------|---------|
| **Goal** | What they need from the player | Ember needs the player to ignore the key |
| **Stakes** | What happens if they fail | Ember faces exposure |
| **Fears** | What they're protecting against | Being discovered |
| **Emotional State** | Current disposition (shifts over time) | Anxious, manipulative, desperate |
| **Model of Player** | What they believe player knows/wants | "Player seems curious but cautious" |

When a player goes off-topic, agents don't "steer back to the plot." They react as their character would.

---

## Gated Goals

Agents pursue goals freely, but certain story beats are **gated** by conditions. When gate conditions are met, the beat surfaces naturally in the next response.

This ensures key story moments happen while maintaining emergent behavior.

---

## Consistency Tracking

With agents giving conflicting information by design, we track:
- **Claims made**: Agents must not contradict their own lies
- **Player reveals**: Agent A shouldn't know what player only told Agent B
- **Ground truth**: System knows reality to manage contradictions

**If an agent contradicts their own earlier lie, immersion shatters.**

---

## Character Lifecycle

Characters are mortal. An agent who no longer has a reason to contact you... doesn't.

| State | Behavior | Player Experience |
|-------|----------|-------------------|
| **Engaged** | Actively pursuing goal, responsive | Regular contact, clear agenda |
| **Cooling** | Goal resolved or blocked | Shorter messages, longer delays |
| **Silent** | No longer initiating | May or may not reply if contacted |
| **Gone** | Will not reply | Disappeared, moved on, or dead |

**Critical rule:** The player never receives explicit confirmation of which state a character is in. They experience silence and wonder.

### Transition Signals

Agents always signal before going silent (so it doesn't feel like a bug):

| Transition | Signal Example |
|------------|----------------|
| Engaged → Cooling | "I need some time to think. I'll be in touch." |
| Cooling → Silent | "I can't keep doing this. Please don't contact me." |
| Silent → Gone | No message - they just stop responding |

The final transition has no message, creating intentional ambiguity.

---

## Channel Inheritance

When a character disappears, a new character can inherit their channel.

**Same number. Different voice.**

The contact in your phone has history. You see old messages. And suddenly - the voice changes.

This creates layers of paranoia:
- Is this really a new person, or is the original character testing me?
- Did they kill the previous character, or is this them under duress?
- If they read the message history, they know what I revealed...

---

## World Layer

A per-player world simulation tracks the player's "footprint" independent of any active character.

- **Exposure level**: 0-100, increases with risky actions
- **Spawn conditions**: New characters appear based on player actions, not plot timing

New characters don't arrive because "the plot needs them." They arrive because the player's actions made them findable.

---

## Inter-Agent Communication

Characters exist beyond the player. They'd talk to each other, share information, scheme, betray.

When agents become aware of each other (through player actions), they evaluate what to share:
- Does sharing help my goal?
- How much do I trust this agent?
- What do I get in return?

**Once two agents are aware of each other, the player loses control of information flow.**

Inter-agent exchanges can:
- Remain invisible to the player
- Surface via behavioral changes
- Create "caught in a lie" moments when agents compare notes

---

## Player Engagement States

| State | Trigger | Agent Behavior |
|-------|---------|----------------|
| **Active** | < 48h silence | Normal pacing |
| **Casual** | 3-5 days | Concerned messages |
| **Dormant** | 7-13 days | Re-engagement hooks |
| **Lapsed** | 14-20 days | Weekly high-value only |
| **Churned** | 21+ days | Pause all messages |

### No "Game Over" State

The game never ends. A churned player who returns finds:
- A world that evolved without them
- Agents in different states than before
- New opportunities, not punishment

This is thematic: the conspiracy continues whether you're watching or not.

---

## Pacing Constraints

Research-backed limits to prevent player overwhelm:

| Metric | Limit | Reasoning |
|--------|-------|-----------|
| Active characters | 2-4 max | Players can track ~4 "hot" NPCs at once |
| Info per message | 3-4 items | Working memory constraint |
| Active plot threads | 2-3 | Beyond this, earlier threads forgotten |
| Messages per day | 4-6 total | Prevents notification fatigue |

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
