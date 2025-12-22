"""Story system: personas, prompts, and narrative context.

This module provides the single source of truth for agent personas
and dynamic prompt generation.
"""

# Import personas submodule to auto-register all personas
from argent.story import personas as _personas  # noqa: F401
from argent.story.persona import (
    AgentPersona,
    list_agents,
    load_character,
)
from argent.story.prompt_builder import PromptBuilder

__all__ = [
    "AgentPersona",
    "PromptBuilder",
    "list_agents",
    "load_character",
]
