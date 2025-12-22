"""Persona definitions for all agents.

Import this module to auto-register all personas.
"""

from argent.story.persona import register_persona
from argent.story.personas.ember import EMBER

# Auto-register all personas on import
register_persona(EMBER)

__all__ = ["EMBER"]
