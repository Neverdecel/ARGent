"""Base agent abstractions for ARGent AI agents."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from uuid import UUID


@dataclass
class AgentContext:
    """Context passed to agents for each invocation."""

    player_id: UUID
    session_id: str
    player_message: str
    conversation_history: list[dict] = field(default_factory=list)
    player_trust_score: int = 0
    player_knowledge: list[str] = field(default_factory=list)
    communication_mode: str = "immersive"  # "immersive" or "web-only"


@dataclass
class AgentResponse:
    """Response from an agent."""

    content: str
    subject: str | None = None
    trust_delta: int = 0
    new_knowledge: list[str] = field(default_factory=list)


class BaseAgent(ABC):
    """Abstract base for all ARGent agents."""

    @property
    @abstractmethod
    def agent_id(self) -> str:
        """Unique agent identifier (e.g., 'ember', 'miro')."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Display name for messages."""
        ...

    @property
    @abstractmethod
    def channel(self) -> str:
        """Communication channel (e.g., 'email', 'sms')."""
        ...

    @abstractmethod
    async def generate_response(
        self, context: AgentContext, player_key: str | None = None
    ) -> AgentResponse:
        """Generate a response to the player's message.

        Args:
            context: The context for this interaction including player message,
                     conversation history, trust scores, and knowledge.
            player_key: The player's unique key (optional, used for betrayal context).

        Returns:
            AgentResponse containing the message content and any state updates.
        """
        ...
