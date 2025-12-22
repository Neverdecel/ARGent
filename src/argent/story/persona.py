"""Agent persona data structures and registry.

Defines the template for agent personas as typed dataclasses.
This is the single source of truth for agent character definitions.

Matches DATA_ARCHITECTURE.md context assembly pipeline.
"""

from dataclasses import dataclass, field


@dataclass
class Background:
    """Agent's core identity and motivations."""

    who_they_are: str
    what_they_want: str
    what_they_hide: str


@dataclass
class PersonalityTrait:
    """A single personality trait with its manifestation."""

    trait: str
    manifestation: str


@dataclass
class VoiceStyle:
    """How the agent writes and communicates."""

    tone: str
    length: str  # "short" | "medium" | "variable"
    punctuation: str
    capitalization: str
    typos: str
    emoji: str
    quirks: list[str] = field(default_factory=list)


@dataclass
class KnowledgeItem:
    """Something the agent knows vs what they tell the player."""

    topic: str
    truth: str
    tells_player: str


@dataclass
class Reaction:
    """How the agent responds to specific player actions."""

    player_action: str
    response: str


@dataclass
class AIRules:
    """Generation rules for the LLM."""

    must_always: list[str] = field(default_factory=list)
    must_never: list[str] = field(default_factory=list)
    style_notes: list[str] = field(default_factory=list)


@dataclass
class ExampleMessage:
    """Example message for few-shot prompting."""

    scenario: str
    content: str


@dataclass
class FirstContactConfig:
    """Configuration for initial contact message generation."""

    situation: str  # What the agent believes is happening
    goal: str  # What the message should achieve
    tone_notes: list[str] = field(default_factory=list)


@dataclass
class AgentPersona:
    """Complete persona definition for an agent.

    This is the template that all agents must follow.
    Enforced via dataclass structure - missing fields = type error.
    """

    # Identity
    agent_id: str
    display_name: str
    channel: str  # "email" | "sms"

    # Character
    background: Background
    personality: list[PersonalityTrait]
    voice: VoiceStyle
    knowledge: list[KnowledgeItem]

    # Behavior
    reactions: list[Reaction]
    trust_building: list[str]
    trust_breaking: list[str]

    # AI generation
    rules: AIRules
    examples: list[ExampleMessage]
    first_contact: FirstContactConfig

    # Optional fields
    avatar: str | None = None  # Filename in static/avatars/, e.g. "ember.png"


# --- Persona Registry ---

_personas: dict[str, AgentPersona] = {}


def register_persona(persona: AgentPersona) -> None:
    """Register a persona in the global registry."""
    _personas[persona.agent_id] = persona


def load_character(agent_id: str) -> AgentPersona:
    """Load character definition by agent ID.

    Referenced in DATA_ARCHITECTURE.md context assembly pipeline (line 395).
    Cached at module level for performance (~600 tokens per agent).

    Args:
        agent_id: The agent identifier (e.g., "ember", "miro")

    Returns:
        The agent's persona definition

    Raises:
        ValueError: If agent_id is not registered
    """
    if agent_id not in _personas:
        raise ValueError(f"Unknown agent: {agent_id}. Available: {list(_personas.keys())}")
    return _personas[agent_id]


def list_agents() -> list[str]:
    """List all registered agent IDs."""
    return list(_personas.keys())


def clear_registry() -> None:
    """Clear the persona registry. Useful for testing."""
    _personas.clear()
