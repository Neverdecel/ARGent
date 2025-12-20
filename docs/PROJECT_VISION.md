# ARGent: AI-Driven Alternate Reality Game

## Project Vision

**ARGent** is an open-source, AI-powered Alternate Reality Game (ARG) where players receive communications from AI agents through real-world channels (email, Telegram) as part of an unfolding mystery/thriller narrative. The game blurs the line between fiction and reality, creating an immersive experience that integrates seamlessly into the player's daily life.

## Core Concept

Players register with their email and phone number, then become unwitting participants in a mystery that unfolds through:

- **Cryptic emails** from unknown senders
- **Telegram messages** from characters who seem to know them
- **Time-sensitive puzzles** that arrive at unexpected moments
- **A web dashboard** where they piece together clues and track the story

The AI agents maintain persistent personalities, remember past interactions, and adapt their communication style based on the player's responses and progress.

## Key Differentiators

| Feature | Traditional ARG | ARGent |
|---------|----------------|------------------|
| Communication | Manual, scripted | AI-generated, adaptive |
| Scalability | Labor-intensive | Automated, infinite players |
| Personalization | One-size-fits-all | Unique experience per player |
| Timing | Fixed schedule | Dynamic, realistic patterns |
| Self-hosting | N/A | Fully self-hostable |

## Target Experience

### A Day in the Life of a Player

**8:47 AM** - Player receives an email from "Dr. Elena Vance" warning them about a security breach at a research facility they've never heard of.

**12:15 PM** - A WhatsApp message from an unknown number: "Did you get Elena's message? Don't trust her. Meet me at the dashboard. -M"

**3:30 PM** - Player checks the dashboard, finds a new document has been "leaked" - a redacted personnel file with a puzzle embedded in it.

**9:22 PM** - Another WhatsApp: "You solved the puzzle. I'm impressed. But you've attracted attention. Stay alert."

**The Next Day** - The story continues, with agents referencing yesterday's events, the player's choices, and adapting the narrative accordingly.

## Technology Stack

### AI Framework: Google ADK + Gemini
We're fully committed to the Google ecosystem for AI agents:

- **Google Agent Development Kit (ADK)** - Multi-agent orchestration framework
- **Gemini 2.5 Pro/Flash** - Cost-efficient, high-quality language models
- **Google Memory Bank** - Managed long-term memory for agent persistence
- **Session State** - Short-term context within conversations

This choice provides:
- Tight integration between components
- Cost efficiency at scale
- Production-ready memory management
- Active development and support from Google

## Technical Philosophy

### Open Source & Self-Hostable
- Complete control over your data
- Run on your own infrastructure (containerized)
- Modify and extend freely
- Community-driven development

### Privacy-First Design
- Minimal data collection
- Player controls their communication preferences
- Clear opt-out mechanisms
- No selling of player data

## Genre: Mystery/Thriller

The initial story framework centers on:

- **A shadowy organization** with unclear motives
- **A whistleblower** who reaches out to players
- **Multiple factions** with competing interests
- **Escalating stakes** as players dig deeper
- **Moral ambiguity** - no clear heroes or villains

## Success Metrics

For MVP/Prototype:
- [ ] Complete single-player story arc (5-7 days)
- [ ] 3+ distinct AI agent personalities
- [ ] Email and WhatsApp integration working
- [ ] Dashboard shows story progression
- [ ] Self-hosting documentation complete

## Project Name

**ARGent** - An ARG powered entirely by AI agents. Every character, every conversation, every story adaptation is driven by autonomous AI agents that remember, react, and evolve with each player.

## References & Inspiration

- **Cicada 3301** - Cryptic puzzles, mysterious organization
- **I Love Bees** - ARG that used phone calls and websites
- **The Black Watchmen** - Modern ARG with ongoing narrative
- **Perplex City** - Puzzle-based ARG with physical/digital blend

---

## Sources

- [Google ADK Memory Documentation](https://google.github.io/adk-docs/sessions/memory/)
- [Agent State and Memory with ADK](https://cloud.google.com/blog/topics/developers-practitioners/remember-this-agent-state-and-memory-with-adk)
- [ADK Documentation Index](https://google.github.io/adk-docs/)
