"""Ember agent implementation using Google ADK.

Ember is an anxious insider who accidentally sent sensitive information
to the wrong email address. They communicate via email and want the player
to delete the cryptic key they received.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

from google.adk import Runner
from google.adk.agents import LlmAgent
from google.adk.sessions import InMemorySessionService
from google.genai import types

from argent.agents.base import AgentContext, AgentResponse, BaseAgent
from argent.config import get_settings
from argent.story import PromptBuilder, load_character

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class EmberAgent(BaseAgent):
    """Ember - the anxious whistleblower agent.

    Ember communicates via email and wants the player to delete a cryptic key
    they accidentally sent to the wrong address. They are anxious, guilt-ridden,
    and trying to control a situation that's slipping away from them.
    """

    APP_NAME = "argent"

    def __init__(
        self,
        gemini_api_key: str,
        model: str = "gemini-2.5-flash",
    ) -> None:
        """Initialize the Ember agent.

        Args:
            gemini_api_key: Google Gemini API key
            model: Gemini model to use (default: gemini-2.5-flash)
        """
        self._model = model

        # Load persona from single source of truth
        self._persona = load_character("ember")
        self._prompt_builder = PromptBuilder()

        # Set the API key in environment for Google GenAI SDK
        os.environ["GOOGLE_API_KEY"] = gemini_api_key

        # Initialize session service for conversation state
        # ADK's InMemorySessionService may not have type stubs in some versions
        session_service: Any = InMemorySessionService
        self._session_service = session_service()

        # Map player sessions to ADK session IDs
        self._player_sessions: dict[str, str] = {}

    @property
    def agent_id(self) -> str:
        """Unique agent identifier."""
        return self._persona.agent_id

    @property
    def display_name(self) -> str:
        """Display name for messages."""
        return self._persona.display_name

    @property
    def channel(self) -> str:
        """Communication channel."""
        return self._persona.channel

    def _create_adk_agent(self, system_prompt: str) -> LlmAgent:
        """Create the ADK agent with the given system prompt."""
        return LlmAgent(
            name="ember",
            model=self._model,
            instruction=system_prompt,
            description="Ember - an anxious insider who accidentally sent something important",
        )

    async def _get_or_create_session(
        self,
        player_id: str,
        session_id: str,
    ) -> str:
        """Get existing ADK session or create new one.

        Args:
            player_id: The player's UUID
            session_id: The conversation session ID

        Returns:
            The ADK session ID
        """
        key = f"{player_id}:{session_id}"

        if key not in self._player_sessions:
            session = await self._session_service.create_session(
                app_name=self.APP_NAME,
                user_id=str(player_id),
                session_id=session_id,
            )
            self._player_sessions[key] = session.id

        return self._player_sessions[key]

    async def generate_response(
        self, context: AgentContext, player_key: str | None = None
    ) -> AgentResponse:
        """Generate Ember's response to a player message.

        Args:
            context: The context for this interaction
            player_key: The player's unique key (for betrayal context)

        Returns:
            AgentResponse containing Ember's reply
        """
        # Build the dynamic system prompt with current context
        settings = get_settings()
        system_prompt = self._prompt_builder.build_system_prompt(
            persona=self._persona,
            trust_score=context.player_trust_score,
            player_knowledge=context.player_knowledge,
            conversation_history=context.conversation_history,
            player_key=player_key,
            communication_mode=context.communication_mode,
            base_url=settings.base_url,
        )

        # Create a fresh agent with the current system prompt
        adk_agent = self._create_adk_agent(system_prompt)

        # Create runner for this agent
        runner = Runner(
            agent=adk_agent,
            app_name=self.APP_NAME,
            session_service=self._session_service,
        )

        # Get or create session for this player/conversation
        adk_session_id = await self._get_or_create_session(
            str(context.player_id),
            context.session_id,
        )

        # Format the player's message
        message = types.Content(
            role="user",
            parts=[types.Part(text=context.player_message)],
        )

        # Generate response
        response_text = ""
        async for event in runner.run_async(
            user_id=str(context.player_id),
            session_id=adk_session_id,
            new_message=message,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        response_text += part.text

        # Clean up the response
        response_text = response_text.strip()

        # Extract subject line if present (format: "Subject: ..." on first line)
        subject = None
        content = response_text

        lines = response_text.split("\n", 1)
        if lines and lines[0].lower().startswith("subject:"):
            subject = lines[0][8:].strip()
            content = lines[1].strip() if len(lines) > 1 else ""

        logger.debug(
            "Response generated: subject=%r, content_length=%d",
            subject,
            len(content),
        )

        # For now, don't calculate trust delta (will be added later)
        return AgentResponse(
            content=content,
            subject=subject,
            trust_delta=0,
            new_knowledge=[],
        )

    async def generate_first_contact(self, key: str) -> AgentResponse:
        """Generate Ember's initial contact message with the cryptic key.

        This is the first message sent to a player when they start the game.
        It contains the key and establishes Ember's anxious, mysterious tone.

        Args:
            key: The player's unique key (format: XXXX-XXXX-XXXX-XXXX)

        Returns:
            AgentResponse containing the initial message with subject line
        """
        # Build the first contact prompt with the key embedded
        system_prompt = self._prompt_builder.build_first_contact_prompt(
            persona=self._persona,
            key=key,
        )

        # Create agent for first contact
        adk_agent = self._create_adk_agent(system_prompt)

        # Create runner
        runner = Runner(
            agent=adk_agent,
            app_name=self.APP_NAME,
            session_service=self._session_service,
        )

        # Create a temporary session for generation
        temp_session = await self._session_service.create_session(
            app_name=self.APP_NAME,
            user_id="system",
            session_id="first-contact-generation",
        )

        # Trigger generation with a simple prompt
        message = types.Content(
            role="user",
            parts=[
                types.Part(
                    text="Write the initial email now. Remember to include the key exactly as provided."
                )
            ],
        )

        # Generate response
        response_text = ""
        async for event in runner.run_async(
            user_id="system",
            session_id=temp_session.id,
            new_message=message,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        response_text += part.text

        response_text = response_text.strip()

        # Try to extract subject line if present (format: "Subject: ..." on first line)
        subject = None
        content = response_text

        lines = response_text.split("\n", 1)
        if lines and lines[0].lower().startswith("subject:"):
            subject = lines[0][8:].strip()  # Remove "Subject:" prefix
            content = lines[1].strip() if len(lines) > 1 else ""

        # Use cryptic fallback if no subject extracted
        if not subject:
            subject = "Thursday"
            logger.warning("No subject extracted from first contact, using fallback")

        logger.info(
            "First contact generated: subject=%r, content_length=%d",
            subject,
            len(content),
        )

        return AgentResponse(
            content=content,
            subject=subject,
            trust_delta=0,
            new_knowledge=[],
        )
