"""Miro agent implementation using Google ADK.

Miro is a calm information broker who reaches out via SMS,
offering to help the player understand what they have.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from google.adk import Runner
from google.adk.agents import LlmAgent
from google.adk.sessions import InMemorySessionService
from google.genai import types

from argent.agents.base import AgentContext, AgentResponse, BaseAgent
from argent.story import PromptBuilder, load_character

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class MiroAgent(BaseAgent):
    """Miro - the calm information broker agent.

    Miro communicates via SMS and offers to help the player understand
    what they've received. They are transactional, curious, and evasive
    about their own background.
    """

    APP_NAME = "argent"

    def __init__(
        self,
        gemini_api_key: str,
        model: str = "gemini-2.5-flash",
    ) -> None:
        """Initialize the Miro agent.

        Args:
            gemini_api_key: Google Gemini API key
            model: Gemini model to use (default: gemini-2.5-flash)
        """
        self._model = model

        # Load persona from single source of truth
        self._persona = load_character("miro")
        self._prompt_builder = PromptBuilder()

        # Set the API key in environment for Google GenAI SDK
        os.environ["GOOGLE_API_KEY"] = gemini_api_key

        # Initialize session service for conversation state
        self._session_service = InMemorySessionService()  # type: ignore[no-untyped-call]

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
            name="miro",
            model=self._model,
            instruction=system_prompt,
            description="Miro - a calm information broker offering help",
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

    async def generate_response(self, context: AgentContext) -> AgentResponse:
        """Generate Miro's response to a player message.

        Args:
            context: The context for this interaction

        Returns:
            AgentResponse containing Miro's reply
        """
        # Build the dynamic system prompt with current context
        system_prompt = self._prompt_builder.build_system_prompt(
            persona=self._persona,
            trust_score=context.player_trust_score,
            player_knowledge=context.player_knowledge,
            conversation_history=context.conversation_history,
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

        # Clean up the response - SMS has no subject lines
        response_text = response_text.strip()

        logger.debug(
            "Miro response generated: content_length=%d",
            len(response_text),
        )

        # For now, don't calculate trust delta (will be added later)
        return AgentResponse(
            content=response_text,
            subject=None,  # SMS has no subject
            trust_delta=0,
            new_knowledge=[],
        )

    async def generate_first_contact(self) -> AgentResponse:
        """Generate Miro's initial contact SMS.

        This is the first message sent to a player after they receive
        Ember's key. Miro reaches out cold, offering to help them
        understand what they have.

        Returns:
            AgentResponse containing the initial SMS message
        """
        # Build the first contact prompt (no key - Miro doesn't have it)
        system_prompt = self._prompt_builder.build_first_contact_prompt(
            persona=self._persona,
            key="",  # Miro doesn't send a key
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
            session_id="miro-first-contact-generation",
        )

        # Trigger generation with a simple prompt
        message = types.Content(
            role="user",
            parts=[
                types.Part(text="Write the initial SMS message now. Keep it short and intriguing.")
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

        logger.info(
            "Miro first contact generated: content_length=%d",
            len(response_text),
        )

        return AgentResponse(
            content=response_text,
            subject=None,  # SMS has no subject
            trust_delta=0,
            new_knowledge=[],
        )
