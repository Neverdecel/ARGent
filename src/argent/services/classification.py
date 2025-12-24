"""Classification service for extracting trust and knowledge from exchanges.

Uses Gemini Flash to analyze player-agent conversations and extract:
- Trust delta (how much did trust change)
- Knowledge revealed (facts the agent disclosed)
- Player intent (what the player was trying to accomplish)
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field

from google import genai

logger = logging.getLogger(__name__)

# Agent goal summaries for context
AGENT_GOALS = {
    "ember": "Wants the player to delete the cryptic key and forget it exists. Anxious about exposure.",
    "miro": "Wants the player to trust them and share information about the key. Opportunistic information broker.",
}


@dataclass
class ExtractionResult:
    """Result of analyzing a player-agent exchange."""

    trust_delta: int  # -20 to +20
    trust_reason: str  # Why the delta
    knowledge_items: list[str] = field(default_factory=list)  # Facts revealed by agent
    player_intent: str = ""  # What player was trying to do
    confidence: float = 1.0  # 0.0 to 1.0


def _build_extraction_prompt(
    player_message: str,
    agent_response: str,
    agent_id: str,
    conversation_context: list[dict],
) -> str:
    """Build the extraction prompt for Gemini."""
    agent_goal = AGENT_GOALS.get(agent_id, "Unknown agent goal")

    # Format recent context (last 3 exchanges)
    context_lines = []
    for msg in conversation_context[-6:]:  # Last 6 messages = 3 exchanges
        role = "PLAYER" if msg.get("role") == "user" else "AGENT"
        content = msg.get("content", "")[:200]  # Truncate for context
        context_lines.append(f"{role}: {content}")

    context_str = "\n".join(context_lines) if context_lines else "(No prior context)"

    return f"""You are analyzing a conversation exchange in an ARG (alternate reality game).

AGENT: {agent_id}
AGENT'S GOAL: {agent_goal}

RECENT CONTEXT:
{context_str}

CURRENT EXCHANGE:
PLAYER: {player_message}
AGENT: {agent_response}

Analyze this exchange and determine:
1. How did the player's message affect their trust with this agent? (scale: -20 to +20)
2. What new information did the AGENT reveal to the player? (list specific facts)
3. What was the player trying to accomplish?

Trust scoring guide:
- Player agrees, cooperates, shares info openly: +5 to +15
- Player asks neutral or clarifying questions: 0 to +5
- Player asks about contradictions with reasoning (e.g., "that doesn't match what you said"): +5 to +10 (shows engagement!)
- Player catches agent in a lie WITH evidence/reasoning: +3 to +8 (they're paying attention - reward this!)
- Player politely pushes for truth: +2 to +5 (persistent but respectful)
- Player reveals they trust another agent more: -5 to -10
- Player aggressively demands answers with hostile tone: -5 to -10
- Player makes threats, insults, or attacks: -15 to -20

IMPORTANT: Curiosity is NOT hostility. A player asking "that doesn't make sense because X" is ENGAGED and should be rewarded. Only penalize actual rudeness, threats, or insults.

Return ONLY valid JSON in this exact format:
{{
  "trust_delta": <integer from -20 to 20>,
  "trust_reason": "<one sentence explaining the trust change>",
  "knowledge_revealed": ["<fact 1>", "<fact 2>"],
  "player_intent": "<what the player was trying to accomplish>",
  "confidence": <float from 0.0 to 1.0>
}}

If the agent revealed no new information, use an empty list for knowledge_revealed.
If you're unsure about the trust delta, use a smaller magnitude and lower confidence."""


async def extract_from_exchange(
    player_message: str,
    agent_response: str,
    agent_id: str,
    conversation_context: list[dict] | None = None,
) -> ExtractionResult:
    """Extract trust delta, knowledge, and intent from a player-agent exchange.

    Args:
        player_message: The player's message
        agent_response: The agent's response
        agent_id: Which agent (ember, miro)
        conversation_context: Recent conversation history

    Returns:
        ExtractionResult with trust_delta, knowledge, and intent
    """
    if conversation_context is None:
        conversation_context = []

    prompt = _build_extraction_prompt(
        player_message=player_message,
        agent_response=agent_response,
        agent_id=agent_id,
        conversation_context=conversation_context,
    )

    try:
        # Get API key from environment
        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            logger.warning("No Gemini API key found, returning neutral extraction")
            return ExtractionResult(
                trust_delta=0,
                trust_reason="No API key available for extraction",
                confidence=0.0,
            )

        # Create client and use async API
        client = genai.Client(api_key=api_key)

        # Use Flash for speed and cost efficiency
        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                temperature=0.1,  # Low temperature for consistent extraction
                max_output_tokens=500,
            ),
        )

        # Parse the JSON response
        response_text = (response.text or "").strip()

        # Handle potential markdown code blocks
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])

        result = json.loads(response_text)

        # Validate and clamp trust_delta
        trust_delta = int(result.get("trust_delta", 0))
        trust_delta = max(-20, min(20, trust_delta))

        return ExtractionResult(
            trust_delta=trust_delta,
            trust_reason=str(result.get("trust_reason", "Unknown")),
            knowledge_items=list(result.get("knowledge_revealed", [])),
            player_intent=str(result.get("player_intent", "")),
            confidence=float(result.get("confidence", 1.0)),
        )

    except json.JSONDecodeError as e:
        logger.warning("Failed to parse extraction response as JSON: %s", e)
        return ExtractionResult(
            trust_delta=0,
            trust_reason="Failed to parse extraction",
            confidence=0.0,
        )
    except Exception as e:
        logger.exception("Extraction failed: %s", e)
        return ExtractionResult(
            trust_delta=0,
            trust_reason=f"Extraction error: {e}",
            confidence=0.0,
        )
