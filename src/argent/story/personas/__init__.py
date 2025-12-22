"""Persona definitions for all agents.

Import this module to auto-register all personas.
"""

from argent.story.persona import register_persona
from argent.story.personas.ember import EMBER
from argent.story.personas.miro import MIRO

# Auto-register all personas on import
register_persona(EMBER)
register_persona(MIRO)

__all__ = ["EMBER", "MIRO"]
