# Features

Player experience and key design decisions.

> **For implementation details, see the code.** This document explains the user-facing experience.

---

## The Experience

The player is **themselves** - a regular person who signs up and gets pulled into an unfolding mystery. They interact with AI agents through **real communication channels** (email, SMS), replying naturally as they would to any contact.

The narrative is **emergent and sandbox-style** - storylines run in parallel, and the AI adapts based on the player's actions, responses, and engagement level.

### The Core Hook

1. Player receives a cryptic email with a unique key
2. Two agents reach out with **conflicting information** about what the key is
3. Player must decide who to trust - choices have consequences
4. The key unlocks an "evidence dashboard" with proof of a cover-up

---

## User Journeys

### Onboarding
```
Sign up (email + phone) → Verify both channels → Click "Start Game"
→ Receive cryptic key email → Ember reaches out → Miro reaches out
```

### Receiving Messages
```
Story triggers event → Agent generates contextual message
→ Sent via email/SMS → Player receives naturally
```

### Player Responds
```
Player replies → System routes to correct agent
→ Agent processes with full context → Agent responds (timing varies by character)
```

### Inactivity
```
Player stops responding → Agents send realistic follow-ups
→ Story pacing slows → When player returns, agents acknowledge gap
```

---

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Messaging channels | Email + SMS | Ember via email (story reason), Miro via SMS |
| Agents (MVP) | 2 (Ember, Miro) | Focused intro, more agents added through play |
| The Key | Unique hash per player | Real credentials to evidence dashboard |
| Dashboard access | Limited (3-5 uses) | Creates tension while allowing return visits |
| Key expiration | None | "Thursday" is narrative tension only |
| Story authoring | YAML + Database | YAML for config, DB for runtime state |
| Web pages | Minimal | Story happens in email/SMS, not on website |

---

## Agent Design

### Memory
- Full conversation history with this player
- Player's story state and choices
- Consistent personality and speech patterns
- Awareness of what other agents have told player
- Trust level that changes based on interactions

### Behavior
- Response timing varies by personality
- Agents reference each other (conflicting information)
- Agents notice player inactivity and react
- Agents maintain consistent version of their truth

### Visibility

| Agent | Channel | Can See Key Usage? | Knows What Key Is? |
|-------|---------|-------------------|-------------------|
| Ember | Email | Yes (system visibility) | Yes (sent it) |
| Miro | SMS | No (outside system) | Partially (knows it's valuable) |

---

## Performance Targets

- 100+ concurrent players
- Message generation < 30s
- Messages delivered within 5-minute window of target time
