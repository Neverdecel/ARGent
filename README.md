# ARGent

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/Neverdecel/argent/actions/workflows/ci.yml/badge.svg)](https://github.com/Neverdecel/argent/actions/workflows/ci.yml)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

<p align="center">
  <img src="resources/landingpage-screenshot.png" alt="ARGent Landing Page" width="400">
</p>

> *You receive an email. Short. Cryptic. A string of characters you don't recognize.*
>
> *"Use this before Thursday."*
>
> *It wasn't meant for you. But now people are reaching out—each with a different story about what you're holding. Each wanting something. You don't know who to trust.*
>
> *Maybe no one.*

---

**ARGent** is an AI-driven alternate reality game where the story finds you through your inbox. No app to check. No game interface. Just messages from AI characters who remember everything, adapt to your choices, and blur the line between fiction and reality.

## The Experience

**Day 1** — A misdirected email arrives. Cryptic content. No context.

**Hours later** — Someone reaches out, panicked: *"I made a mistake. Please don't share that with anyone."*

**The next morning** — A message from an unknown number: *"Heard you received something interesting. I might be able to help."*

How did they get your number? Who's telling the truth? What did you actually receive?

**Trust is the game.** Not puzzles. Not plot points. Deciding who to believe—and living with the consequences.

## How It Works

1. **Register** with your email (and optionally phone)
2. **Receive** a cryptic misdirected message containing an access key
3. **Navigate** conflicting stories from AI agents with their own agendas
4. **Decide** who to trust as the narrative adapts to your choices

Every player's experience is unique. The AI agents remember your conversations, notice what you reveal (and what you hide), and reference your past decisions.

## Play Modes

| Mode | Description |
|------|-------------|
| **Immersive** | Messages arrive via real email and SMS throughout your day |
| **Web-Only** | All messages in a browser inbox—no phone required |

## The Agents

Characters reach out through different channels. Each has their own personality, their own claims, their own angle.

| Agent | Channel | Vibe |
|-------|---------|------|
| **Ember** | Email | Anxious insider who made a mistake. Wants to undo it. |
| **Miro** | SMS | Smooth information broker. Helpful, but what's their angle? |
| **Cipher** | — | The intended recipient. Cold. Technical. A problem to solve. |
| **Kessler** | — | Corporate fixer. Polite. Professional. Unsettling. |

*More agents enter based on your choices and how the story escalates.*

## Features

- **Real channels** — Messages arrive via email and SMS, not a game interface
- **Persistent memory** — Agents remember everything across conversations
- **Adaptive narrative** — Story pacing adjusts to your engagement
- **Trust mechanics** — Relationships evolve based on your choices
- **Self-hostable** — Run your own instance, own your data

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Google Gemini API key

### Quick Start

```bash
git clone https://github.com/Neverdecel/argent.git
cd argent
cp .env.example .env.local
# Add your GEMINI_API_KEY to .env.local

docker compose up -d
```

Open http://localhost:8000 and register. Use **web-only mode** for quick testing.

### Development

```bash
# Run tests
source .venv/bin/activate
pytest

# Test agent prompts
python scripts/test_first_contact.py --prompt-only

# Test with API
docker compose exec app python /app/scripts/test_first_contact.py
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| AI Agents | Google ADK + Gemini 2.5 Flash |
| Backend | FastAPI (Python) |
| Database | PostgreSQL |
| Queue | Redis + Huey |
| Email | Mailgun |
| SMS | Twilio |

## Project Status

ARGent is in **active development**. Current state:

- [x] Onboarding flow with verification
- [x] Web inbox for browser-based play
- [x] Ember agent with dynamic prompts
- [x] Avatar and conversation UI
- [x] Docker deployment
- [ ] Miro agent (SMS)
- [ ] Multi-agent orchestration
- [ ] Long-term memory persistence

## Documentation

| Topic | Link |
|-------|------|
| Project Vision | [docs/PROJECT_VISION.md](docs/PROJECT_VISION.md) |
| Story Premise | [docs/story/PREMISE.md](docs/story/PREMISE.md) |
| Agent Design | [docs/agents/AGENTS.md](docs/agents/AGENTS.md) |
| Tech Decisions | [docs/TECHNOLOGY_CHOICES.md](docs/TECHNOLOGY_CHOICES.md) |

## Contributing

ARGent is open source under the MIT License. We're building in the open—contributions welcome.

## License

[MIT](LICENSE)

---

<p align="center">
  <strong>ARGent</strong> — Where AI agents play the game with you.
</p>
