# ARGent

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/Neverdecel/argent/actions/workflows/ci.yml/badge.svg)](https://github.com/Neverdecel/argent/actions/workflows/ci.yml)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

<p align="center">
  <img src="resources/landingpage-screenshot.png" alt="ARGent Landing Page" width="400">
</p>

**An AI-driven alternate reality game**

ARGent is an open-source alternate reality game (ARG) powered by AI agents. Players receive messages from AI characters through real-world channels—email and SMS—as part of an unfolding mystery narrative. The game blurs the line between fiction and reality, creating an immersive experience that integrates into daily life.

## How It Works

1. **Register** with your email and phone number
2. **Receive** a cryptic misdirected message containing an access key
3. **Navigate** conflicting information from AI agents who each have their own agenda
4. **Decide** who to trust as the story adapts to your choices

Every player gets a unique experience. The AI agents remember your conversations, adapt to your engagement style, and reference your past decisions.

## Features

- **Real Communication Channels** - Messages arrive via email and SMS, not a game interface
- **Persistent AI Agents** - Characters with distinct personalities that remember everything
- **Adaptive Narrative** - Story pacing and content adjust based on your choices and engagement
- **Trust Mechanics** - Your decisions affect relationships with agents and unlock different story paths
- **Self-Hostable** - Run your own instance with full control over your data

## Play Modes

ARGent supports two ways to play:

| Mode | Description |
|------|-------------|
| **Immersive** | Messages arrive via real email and SMS, blurring the line between game and reality |
| **Web-Only** | All messages appear in a browser inbox—no phone number required |

Choose your experience during registration.

## Tech Stack

| Component | Technology |
|-----------|------------|
| AI Agents | Google ADK + Gemini 2.5 |
| Memory | Google Memory Bank (Vertex AI) |
| Backend | FastAPI (Python) |
| Database | PostgreSQL |
| Task Queue | Redis + Huey |
| Email | Mailgun |
| SMS | Twilio |
| Deployment | Docker Compose / k3s |

## Project Status

ARGent is in **active development**. The core platform is functional:

- **Onboarding flow** - Complete with email and phone verification
- **Web inbox** - Browser-based messaging for non-immersive play
- **Dual play modes** - Choose between real channels or web-only
- **AI Agents** - Ember agent powered by Google ADK + Gemini 2.5 Flash
- **Infrastructure** - Docker deployment, CI/CD, database migrations

We're building in the open—the docs folder contains comprehensive specifications for the story system, technical architecture, and agent personalities.

## Documentation

- [Project Vision](docs/PROJECT_VISION.md) - Core concept and goals
- [Features & Requirements](docs/FEATURES_AND_REQUIREMENTS.md) - Detailed specifications
- [Technology Choices](docs/TECHNOLOGY_CHOICES.md) - Architecture decisions
- [Story System](docs/STORY_SYSTEM.md) - How the narrative engine works
- [Data Architecture](docs/DATA_ARCHITECTURE.md) - Database and memory design
- [AI Agents](docs/agents/AGENTS.md) - Agent architecture and implementation
- [Web Inbox](docs/WEB_INBOX.md) - Non-immersive play mode
- [Immersion Design](docs/IMMERSION_DESIGN.md) - Agent interaction design

### Story & Characters

- [Premise](docs/story/PREMISE.md) - The opening hook
- [Ember](docs/story/agents/ember.md) - The anxious insider (Email)
- [Miro](docs/story/agents/miro.md) - The information broker (SMS)

## Getting Started

> Coming soon—implementation is in progress.

## Contributing

ARGent is open source under the MIT License. Contributions are welcome once the core implementation is in place.

## License

[MIT](LICENSE)

---

**ARGent** - Where AI agents play the game with you.
