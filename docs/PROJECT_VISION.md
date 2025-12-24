# ARGent: Where AI Characters Feel Alive

## Vision

What if the characters in your inbox felt genuinely alive?

Not chatbots following scripts. Not AI assistants awaiting commands. **Entities** — with memories that persist, personalities that stay consistent, and goals they pursue whether you're watching or not.

ARGent is an alternate reality game built on a simple premise: the AI characters who contact you should feel as real as the messages they send through.

---

## The Three Pillars

Every design decision in ARGent serves one of three pillars of agent realism:

### 1. Memory

Agents remember. Not just what you said five minutes ago — what you revealed three days ago, what you promised last week, what you're pretending you forgot.

- **Persistent context** across sessions and days
- **Fact extraction** from conversations (agents won't repeat themselves)
- **Claims tracking** to prevent self-contradiction
- **Long-term semantic memory** for meaningful references to the past

When Ember mentions "that thing you said about trust" — she's not hallucinating. She remembers.

### 2. Character

Agents have consistent personalities that don't break. Each one has:

- **Goals** — What they need from you
- **Stakes** — What happens if they fail
- **Fears** — What they're protecting against
- **Emotional state** — How they feel right now, based on what's happened
- **Model of you** — What they believe you know, want, and will do

An agent isn't a narrator. **An agent is a person who needs something.**

When you go off-topic, they don't "steer back to the plot." They react as their character would — confused, impatient, suspicious, or amused.

### 3. Autonomy

Agents act on their own motivations. They pursue goals, not scripts.

- **Proactive contact** — Agents reach out when they have reason to, not on a fixed schedule
- **Goal-directed behavior** — Every message serves the agent's interests
- **Adaptive strategy** — Agents change approach when their current one isn't working
- **Inter-agent dynamics** — Agents exist in relation to each other, not just to you

The story emerges from this collision: agents pursuing goals against a player who has genuine agency.

---

## Why an ARG?

An alternate reality game is the perfect canvas for agent realism. The fiction arrives through real channels — your actual inbox, your phone, your browser. There's no "game interface" to remind you it's fiction.

When a message arrives and you're not sure if it's real — that's immersion no app can achieve.

### What Makes ARGent Different

| Dimension | Traditional ARG | ARGent |
|-----------|-----------------|--------|
| Characters | Pre-scripted responses, limited branches | Persistent entities with real memory |
| Personalization | One story fits all | Unique experience shaped by your choices |
| Scale | Labor-intensive, small audiences | Automated, unlimited players |
| Consistency | Characters may contradict themselves | Claims tracking prevents breaks |
| Mortality | Characters exist until the story ends | Characters can fade, go silent, or die |

---

## Design Principles

### The Character Exists Whether You're Watching or Not

Time passes. Events happen. The world doesn't pause when you close your inbox.

If you go silent for a week, agents notice. They might reach out with concern, or give up and move on. The conspiracy continues without you.

### Agents Are Mortal

Characters who no longer have a reason to contact you... don't. They can go cold, go silent, or disappear entirely.

You never receive explicit confirmation of their state. You experience silence and wonder.

### Trust Is the Game

The core mechanic isn't puzzles or clues — it's deciding who to believe. Multiple agents with conflicting stories, each with their own agenda. You choose who to trust. You live with the consequences.

### Consequences Without Dead Ends

Mistakes matter, but the story doesn't end. Bad choices create ripples — harder situations, lost opportunities, new threats — but never a "game over."

---

## The First Story

ARGent launches with a mystery/thriller narrative:

You receive a misdirected email. A cryptic key. No context.

Then people start reaching out. Each with a different story about what you're holding. Each wanting something from you.

**Ember** (email) — Anxious insider. Wants you to delete the key and forget this happened. Something's at stake for her.

**Miro** (SMS) — Smooth operator. Wants to help you understand what you have. Helpful, but what's their angle?

More characters enter based on your choices and how visible you become.

---

## Technology Choices

Our tech stack is chosen specifically to enable agent realism:

| Component | Choice | Why |
|-----------|--------|-----|
| AI Framework | Google ADK + Gemini | Native memory management, multi-agent orchestration |
| Models | Gemini 2.5 Flash/Pro | Cost-efficient at scale with strong reasoning |
| Backend | FastAPI + PostgreSQL | Async-first, relational model for complex state |
| Queue | Redis + Huey | Background jobs for realistic timing |
| Channels | Mailgun, Twilio | Real email and SMS for immersion |

### Open Source & Self-Hostable

- Run on your own infrastructure
- Own your data
- Modify and extend freely
- Privacy-first by design

---

## Success Criteria

How we know the vision is working:

| Signal | What It Indicates |
|--------|-------------------|
| **Substantive replies** | Player treats agents as real people |
| **Unprompted contact** | Player initiates without being messaged first |
| **Testing behavior** | Player tries to verify agent claims |
| **Cross-agent references** | Player mentions one agent to another |
| **Suspicion of leaks** | Player questions how an agent knew something |
| **Return after silence** | Player re-engages after going quiet |

The ultimate test: when a player isn't sure whether the message they just received is part of the game.

---

## References & Inspiration

- **Cicada 3301** — Cryptic puzzles, mysterious organization
- **I Love Bees** — ARG through real-world channels (phone calls, websites)
- **The Black Watchmen** — Ongoing narrative ARG
- **Perplex City** — Puzzle-based with physical/digital blend

---

*ARGent: Persistent entities, not stateless functions.*
