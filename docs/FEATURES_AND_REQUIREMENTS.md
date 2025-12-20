# Features & Requirements

## Player Experience Summary

The player is **themselves** - a regular person who signs up and gets pulled into an unfolding mystery. They interact with AI agents through **real communication channels** (email, Telegram), replying naturally as they would to any contact. A **player dashboard** lets them track the story, review clues, and understand the web of characters they're dealing with.

The narrative is **emergent and sandbox-style** - multiple storylines run in parallel, and the AI adapts based on the player's actions, responses, and engagement level. If a player goes quiet, characters notice and react realistically.

### The Core Hook

The player receives a cryptic email with a unique key/hash. They don't know what it is. Two agents reach out with **conflicting information** about what the key is and what to do with it. The player must decide who to trust - and their choices have consequences.

**The key is actually:** Access credentials to an "evidence dashboard" containing proof of a corporate cover-up. The player can eventually access this dashboard if they piece together how to use the key.

---

## Core User Journeys

### 1. Onboarding Flow

```
Player discovers game → Signs up (email + Telegram) → Verifies BOTH channels
→ Brief dashboard intro → Receives "The Key" email (immersive start)
→ Ember reaches out (email) → Miro reaches out (Telegram DM)
```

**Requirements:**
- [ ] Registration with email and Telegram username
- [ ] **Verify email upfront** (ensures future emails don't go to spam)
- [ ] **Verify Telegram upfront** (bot can DM player directly, enhances immersion)
- [ ] Dashboard walkthrough explaining what to expect
- [ ] Player sets timezone and any quiet hours (optional, since story-driven)
- [ ] Consent and terms (this is an ARG, expect messages at odd hours)
- [ ] **Generate unique key/hash for this player** (stored in DB)
- [ ] **Send "The Key" email** (cryptic message with unique hash)
- [ ] Ember contact within hours (panicked follow-up via email)
- [ ] Miro contact within a day (smooth Telegram DM - no "add contact" friction)

### 2. Receiving Communications

```
Scheduler triggers → Agent generates contextual message →
Sent via appropriate channel → Player receives notification
```

**Requirements:**
- [ ] Email delivery with proper formatting, sender names, subjects
- [ ] Telegram messages that feel personal (not templated)
- [ ] Agents have distinct communication styles
- [ ] Messages reference past interactions and player responses
- [ ] Story-driven timing (agents message when it makes narrative sense)
- [ ] Support for attachments/images (leaked documents, photos)

### 3. Player Responds

```
Player replies via email/Telegram → System receives message →
Routes to correct agent → Agent processes with full context →
Agent responds (immediately or later, based on character)
```

**Requirements:**
- [ ] Inbound email parsing (reply detection)
- [ ] Telegram webhook for incoming messages
- [ ] Route message to the correct agent based on thread/number
- [ ] Agent has access to full conversation history
- [ ] Agent has access to player's story state
- [ ] Response timing varies by agent personality (some reply fast, some don't)

### 4. Main Site (Landing + Registration)

The main site is minimal - just enough to get players registered and started.

```
Player visits site → Reads landing page → Registers (email + Telegram)
→ Verifies email → Verifies Telegram → Clicks "Start Game" → Story begins
```

**Requirements:**
- [ ] Landing page explaining the experience (without spoilers)
- [ ] Registration form (email + Telegram username)
- [ ] Email verification (click link in email)
- [ ] Telegram verification (start chat with verification bot)
- [ ] "Start Game" button that triggers the story
- [ ] Simple, mysterious aesthetic
- [ ] Mobile-friendly

**NOT included (intentionally):**
- No dashboard or timeline
- No character profiles
- No message archive
- The story happens in email/Telegram, not on a website

### 5. Inactivity Handling

```
Player stops responding → Agents notice → Send realistic follow-ups →
Story pacing slows → When player returns, story acknowledges gap
```

**Requirements:**
- [ ] Track player response patterns and engagement
- [ ] Agents send natural "where are you?" type messages
- [ ] Story progression slows but doesn't halt completely
- [ ] When player re-engages, agents acknowledge the time gap
- [ ] Optional "catch me up" summary on dashboard

### 6. The Evidence Dashboard (Story Element)

```
Player learns URL → Enters their unique key → Views evidence →
Ember detects access (system logs it) → Story escalates
```

A separate, in-fiction "evidence dashboard" that players can access with their key. This is NOT the player dashboard - it's a story element.

**Requirements:**
- [ ] **Separate web page** styled as an internal corporate system
- [ ] **Key validation** - player's unique hash grants access
- [ ] **Access logging** - system records when key is used
- [ ] **Ember visibility** - Ember can "see" that player accessed it (triggers story events)
- [ ] **Content**: Evidence of cover-up (logs, documents, records)
- [ ] **One-time or limited access?** (TBD - story implications)

---

## Agent Behavior Requirements

### Memory & Context

| Memory Type | What It Stores | Example |
|-------------|----------------|---------|
| **Conversation History** | All messages with this player | "Last time we spoke, you said..." |
| **Player State** | Choices, knowledge, story progress | "You already know about the facility" |
| **Agent Personality** | Consistent traits, speech patterns | Formal vs casual, trusting vs paranoid |
| **Cross-Agent Awareness** | What other agents have told player | "I heard you've been talking to Marcus" |
| **Relationship Dynamics** | How agent feels about player | Trust level changes based on interactions |

### Timing & Realism

- Agents have "personalities" that affect response timing
  - Paranoid character: responds at odd hours, delayed
  - Eager ally: responds quickly, sometimes too quickly
  - Busy executive: responds during "business hours"
- Story events can trigger urgent, immediate messages
- Natural delays (typing indicators in Telegram)

### Inter-Agent Dynamics

- Agents can reference each other
- **Conflicting information from different agents** (core mechanic)
- Agents may warn player about other agents
- Some agents may "find out" player talked to rivals

### Agent Visibility & Knowledge (MVP)

| Agent | Channel | Can See Key Usage? | Knows What Key Is? |
|-------|---------|-------------------|-------------------|
| **Ember** | Email | YES - has system visibility | YES - sent it, knows exactly what it accesses |
| **Miro** | Telegram | NO - outside the system | PARTIALLY - knows it's valuable, not specifics |

**Implications:**
- If player tells Ember they won't use key, then uses it → Ember knows, trust breaks
- If player tells Miro they used the key → Miro can't verify, has to trust player
- Ember's visibility = more controlling but also more vulnerable (player can test them)
- Miro's distance = more neutral but also more transactional

### Conflicting Information (MVP)

Agents give **different answers** to the same questions:

| Topic | Ember Says | Miro Says |
|-------|------------|-----------|
| What the key is | "Old password, nothing important" | "Credentials to something valuable" |
| What's on the dashboard | "Some files, not your concern" | "Evidence someone wants buried" |
| The "Thursday" urgency | "Ignore it, doesn't matter" | "Someone expected delivery" |
| What player should do | "Delete it, forget this happened" | "Explore it, know your leverage" |

**System requirement:** Agents must maintain their version of the truth consistently across all conversations.

---

## Narrative System Requirements

### Sandbox Structure

```
┌─────────────────────────────────────────────┐
│             STORY WORLD                      │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐     │
│  │Thread A │  │Thread B │  │Thread C │     │
│  │Corporate│  │Whistle- │  │Personal │     │
│  │Conspiracy│ │blower   │  │Mystery  │     │
│  └────┬────┘  └────┬────┘  └────┬────┘     │
│       │            │            │           │
│       └────────────┼────────────┘           │
│                    │                        │
│            ┌───────▼───────┐               │
│            │  PLAYER       │               │
│            │  (themselves) │               │
│            └───────────────┘               │
└─────────────────────────────────────────────┘
```

**Requirements:**
- [ ] Multiple parallel storylines that can intersect
- [ ] Player engagement determines which threads develop
- [ ] Storylines can influence each other
- [ ] New threads can emerge from player actions
- [ ] Story state machine tracks progress per thread
- [ ] Coherent world state across all agents

### Emergent Narrative

- AI adapts story beats based on player responses
- Player theories/guesses can be incorporated
- Dead ends acknowledged, not ignored
- Player agency feels real, not illusory

---

## Web Pages (MVP)

### Main Site (phantomprotocol.io)

| Page | Purpose |
|------|---------|
| `/` | Landing - mysterious intro, "Enter" button |
| `/register` | Email + Telegram registration form |
| `/verify/email` | Email verification callback |
| `/verify/telegram` | Instructions to verify Telegram |
| `/start` | Final "Start Game" button |
| `/settings` | Pause game, delete account (minimal) |

### Story Pages (Subdomains - built as needed)

| Page | Purpose | When Built |
|------|---------|------------|
| `evidence.phantomprotocol.io` | Corporate evidence dashboard | MVP (core to story) |
| (future subdomains) | Other story elements | When story requires |

**Philosophy:** The story happens in email and Telegram. Web pages exist only for:
1. Getting players registered
2. Story-driven elements (like the evidence dashboard)

---

## Communication Channel Requirements

### Email

| Requirement | Description |
|-------------|-------------|
| Custom sender names | "Dr. Elena Vance <elena.vance@meridian-research.com>" |
| Threaded replies | Maintain conversation threads |
| HTML formatting | Rich emails with styled content |
| Attachments | PDFs, images for "leaked documents" |
| Inbound parsing | Handle player replies, extract content |
| Bounce handling | Detect failed deliveries |

### Telegram

| Requirement | Description |
|-------------|-------------|
| Verification bot | Single bot for registration verification |
| Agent bots | Separate bot per character (Miro, future agents) |
| Upfront verification | Player starts chat with verification bot during registration |
| DM capability | Once verified, agent bots can DM player directly |
| Personal feel | Messages feel like they're from a person |
| Media support | Send images, documents, voice messages |
| Typing indicators | "typing..." action before messages for realism |
| Inbound webhooks | Receive and process player replies via Bot API |
| Bot profiles | Custom names, avatars, descriptions per character |

**Verification Flow:**
1. Player enters Telegram username during registration
2. Site shows: "Start a chat with @PhantomVerifyBot and send /verify"
3. Bot confirms verification, stores player's chat_id
4. Now Miro (and future agents) can DM the player directly

**Why Telegram over WhatsApp:**
- Each agent = separate bot (unique identity, no shared numbers)
- Bots can initiate DMs after user starts chat (perfect for immersion)
- Free, official API (no risk of breaking)
- Easy self-hosting with webhooks
- Rich features: typing indicators, media, buttons
- No business verification required

### Future: Voice

| Requirement | Description |
|-------------|-------------|
| Voicemail drops | Agents leave cryptic voicemails |
| Call simulation | Maybe: actual voice calls with AI |
| Transcription | Voice responses converted to text for agent processing |

---

## Non-Functional Requirements

### Self-Hosting

- Single `docker-compose up` deployment
- All configuration via environment variables
- Works with standard SMTP for email
- Telegram bot setup documented
- SQLite for simple deployments, PostgreSQL for scale
- Clear documentation for setup

### Privacy & Security

- Passwords hashed, tokens secure
- Player data exportable (GDPR-style)
- Clear data deletion process
- No analytics/tracking without consent
- Communication content encrypted at rest

### Performance

- Handle 100+ concurrent players (MVP target)
- Message generation < 30 seconds
- Dashboard loads < 2 seconds
- Scheduled messages delivered within 5-minute window of target time

---

## Decisions Made

| Question | Decision | Rationale |
|----------|----------|-----------|
| **Messaging platform** | Telegram + Email | Ember via email (story reason), Miro via Telegram bot |
| **Number of agents (MVP)** | 2 agents (Ember, Miro) | Focused intro, more agents introduced through play |
| **Story authoring** | YAML + Database hybrid | YAML for static config (agents, triggers), DB for runtime state |
| **AI framework** | Google ADK + Gemini | Cost-efficient, great memory system, active development |
| **The Key** | Unique hash per player | Real credentials to evidence dashboard |
| **Evidence Dashboard** | Separate hosted page | In-fiction corporate system players can access |
| **Access visibility** | Ember can detect | Logged in system, triggers story events |
| **Dashboard access model** | Limited (3-5 uses per key) | Creates tension while allowing return visits |
| **Key expiration** | No expiration | "Thursday" is narrative tension only; agents react to missed deadline |
| **Multi-language** | English only (MVP) | Defer i18n architecture |
| **Email domain** | Anonymous/generic sender | Ember uses spoofed/anonymous sender for MVP |
| **Dashboard content** | Minimal (3-5 items) | 2-3 logs, 1 redacted doc, 1 email fragment |

---

## Open Questions

All key questions have been resolved. See Decisions Made table above.

---

## Next Steps

1. ~~Map requirements to specific technologies~~ → See TECHNOLOGY_CHOICES.md
2. ~~Design full Ember and Miro profiles~~ → See `/docs/story/agents/`
3. ~~Create system architecture diagram~~ → See TECHNOLOGY_CHOICES.md
4. ~~Map opening week timeline~~ → See OPENING_WEEK_TIMELINE.md
5. ~~Design the evidence dashboard page~~ → See THE_TRUTH.md + dashboard content decisions
