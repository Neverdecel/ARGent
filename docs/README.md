# ARGent Documentation

**Principle:** Code is the best documentation. These docs provide high-level context and design rationale, not implementation details.

## Quick Navigation

| Document | Purpose |
|----------|---------|
| [PROJECT_VISION.md](PROJECT_VISION.md) | What ARGent is and why it exists |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Tech stack, key decisions, and system overview |
| [FEATURES.md](FEATURES.md) | User journeys and feature decisions |
| [ROADMAP.md](ROADMAP.md) | Development roadmap with checkable milestones |

## Story Bible

| Document | Purpose |
|----------|---------|
| [story/PREMISE.md](story/PREMISE.md) | The hook, characters, and narrative foundation |
| [story/THE_TRUTH.md](story/THE_TRUTH.md) | Ground truth - what's real vs what agents claim |
| [story/STORY_SYSTEM.md](story/STORY_SYSTEM.md) | Design philosophy for emergent narrative |
| [story/IMMERSION.md](story/IMMERSION.md) | Principles for believable agent behavior |
| [story/TIMELINE.md](story/TIMELINE.md) | Opening week narrative beats |

## Implementation Reference

For implementation details, see the code:

- **Agents**: `src/agents/` - Ember, Miro, persona system
- **API**: `src/api/` - Registration, inbox, webhooks
- **Models**: `src/models/` - Database schema
- **Services**: `src/services/` - Email, SMS, scheduling
- **Scheduler**: `src/scheduler/` - Event triggers
