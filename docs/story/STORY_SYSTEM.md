# Story System Design

> **For implementation details, see the code.** This document describes the design philosophy.

---

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

- **Facts**: What is true in this world
- **Events**: What has happened (and who knows about it)
- **Player Knowledge**: What the player has learned (agents won't re-explain)

### Characters (Agents)

Each character is defined by their **personality**, **goals**, **knowledge**, and **relationships**.

- **Personality**: Traits, speech style, quirks
- **Goals**: Primary, secondary, and hidden motivations
- **Knowledge**: What they know vs. what they don't know
- **Relationships**: How they relate to other characters
- **Behavior**: Response patterns, active hours, channels

### Story Threads

A **Thread** is an ongoing storyline. Multiple threads run simultaneously and can influence each other.

- **Characters**: Who is involved
- **State**: Current phase of the thread
- **Milestones**: Key story beats (can happen in various orders)
- **Connections**: How this thread links to others

### Events

**Events** are things that happen in the world. They can be triggered by player actions, time, or conditions.

---

## Ripple Effect System

Player choices don't create branches - they create **ripples** that influence future events and character behaviors.

**Example:**
1. Player receives conflicting info from Ember and Miro
2. Player tells Ember they believe Miro
3. Ember's trust drops, Miro's trust rises
4. Ember's future messages become more desperate
5. Miro becomes more confident, shares more
6. Other characters monitoring the situation take note

---

## Timeline & Pacing

### Time-Based Events
Some events happen on a schedule regardless of player action.

### Player-Gated Events
Some events wait for player action (trust thresholds, explicit questions, etc.).

### Pacing Adaptation
System adapts message frequency and event spacing based on player engagement level.

---

## Content Authoring

### What Authors Define vs. What AI Generates

| Element | Author Defines | AI Generates |
|---------|----------------|--------------|
| Characters | Personality, goals, relationships | Actual dialogue |
| World | Facts, setting, rules | Maintaining consistency |
| Milestones | Key story beats | When/how they occur |
| Threads | Structure, connections | Pacing, transitions |
| Events | Triggers, intents | Message content |

---

## Handling Players "Breaking" the Story

When players go off-script or try to break immersion, agents incorporate it into the narrative:

- **Meta-references**: Agent expresses concern about player's mental state
- **Off-topic**: Agent is confused but tries to refocus
- **Confrontational**: Agent interprets it within the story world

This keeps immersion intact while making player behavior part of the story.

---

## Future Considerations

1. **Fresh content for ongoing play**
   - Modular story packs that plug into existing world
   - Seasonal events affecting all players

2. **Multiplayer / Shared world**
   - Cross-player ripple effects
   - Collaborative discoveries
