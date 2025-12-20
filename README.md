# ARGent

**An AI-driven alternate reality game**

ARGent is an open-source alternate reality game (ARG) powered by AI agents. Players receive messages from AI characters through real-world channels—email and Telegram—as part of an unfolding mystery narrative. The game blurs the line between fiction and reality, creating an immersive experience that integrates into daily life.

## How It Works

1. **Register** with your email and Telegram
2. **Receive** a cryptic misdirected message containing an access key
3. **Navigate** conflicting information from AI agents who each have their own agenda
4. **Decide** who to trust as the story adapts to your choices

Every player gets a unique experience. The AI agents remember your conversations, adapt to your engagement style, and reference your past decisions.

## Features

- **Real Communication Channels** - Messages arrive via email and Telegram, not a game interface
- **Persistent AI Agents** - Characters with distinct personalities that remember everything
- **Adaptive Narrative** - Story pacing and content adjust based on your choices and engagement
- **Trust Mechanics** - Your decisions affect relationships with agents and unlock different story paths
- **Self-Hostable** - Run your own instance with full control over your data

## Tech Stack

| Component | Technology |
|-----------|------------|
| AI Agents | Google ADK + Gemini 2.5 |
| Memory | Google Memory Bank (Vertex AI) |
| Backend | FastAPI (Python) |
| Database | PostgreSQL |
| Task Queue | Redis + Huey |
| Email | Mailgun/Resend |
| Messaging | Telegram Bot API |
| Deployment | Docker Compose / k3s |

## Project Status

ARGent is currently in the **design and documentation phase**. We're building in the open—the docs folder contains comprehensive specifications for the story system, technical architecture, and agent personalities.

## Documentation

- [Project Vision](docs/PROJECT_VISION.md) - Core concept and goals
- [Features & Requirements](docs/FEATURES_AND_REQUIREMENTS.md) - Detailed specifications
- [Technology Choices](docs/TECHNOLOGY_CHOICES.md) - Architecture decisions
- [Story System](docs/STORY_SYSTEM.md) - How the narrative engine works
- [Data Architecture](docs/DATA_ARCHITECTURE.md) - Database and memory design

### Story & Characters

- [Premise](docs/story/PREMISE.md) - The opening hook
- [Ember](docs/story/agents/ember.md) - The anxious insider (Email)
- [Miro](docs/story/agents/miro.md) - The information broker (Telegram)

## Getting Started

> Coming soon—implementation is in progress.

## Contributing

ARGent is open source under the MIT License. Contributions are welcome once the core implementation is in place.

## License

[MIT](LICENSE)

---

**ARGent** - Where AI agents play the game with you.
