# AI Agents Implementation

This document describes the AI agent architecture in ARGent.

## Overview

ARGent uses Google ADK (Agent Development Kit) with Gemini 2.5 Flash to power AI agents that respond to player messages in character. Each agent has a distinct personality, goals, and communication style.

## Architecture

```
Player Message
      ↓
Inbox API (compose_message)
      ↓
Load Context (trust, knowledge, history)
      ↓
Agent.generate_response()
      ↓
ADK Runner → Gemini API
      ↓
Store Response → WebInboxService
      ↓
Player sees reply
```

## Components

### Base Classes (`src/argent/agents/base.py`)

- **AgentContext**: Contains player_id, session_id, message, conversation history, trust score, and knowledge
- **AgentResponse**: Contains response content, optional subject, trust delta, and new knowledge
- **BaseAgent**: Abstract base class defining the agent interface

### Ember Agent (`src/argent/agents/ember.py`)

Ember is the first agent - an anxious insider who accidentally sent a cryptic key to the wrong recipient.

**Key Features:**
- Uses `InMemorySessionService` for ADK session state
- `generate_response()` for replies to player messages
- `generate_first_contact()` for the initial cryptic key message

### Prompt System (`src/argent/agents/prompts/`)

System prompts are built dynamically based on:
- Agent personality and voice patterns
- Current player trust level
- Player knowledge (what they've revealed)
- Conversation history length

## Message Flow

### First Contact (Start Game)
1. Player clicks "Start Game"
2. System generates unique key (XXXX-XXXX-XXXX-XXXX format)
3. `EmberAgent.generate_first_contact(key)` creates cryptic initial message
4. Message stored via WebInboxService with session_id for threading

### Ongoing Conversation
1. Player composes reply in inbox
2. System loads context: trust score, knowledge, history
3. `EmberAgent.generate_response(context)` generates reply
4. Response stored in same session_id for threading

## Configuration

Environment variables (`.env.local`):
```
GEMINI_API_KEY=your-api-key
GEMINI_MODEL=gemini-2.5-flash
AGENT_RESPONSE_ENABLED=true
```

## Adding New Agents

1. Create `src/argent/agents/<agent_name>.py` extending `BaseAgent`
2. Create prompts in `src/argent/agents/prompts/<agent_name>.py`
3. Register in `src/argent/api/inbox.py` `_get_agent()` function
4. Update `src/argent/agents/__init__.py` exports

## Dependencies

The agents feature requires the `agents` optional dependency:
```bash
pip install ".[agents]"
```

This installs `google-adk` and related packages.
