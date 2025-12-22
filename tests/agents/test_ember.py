"""Tests for EmberAgent and prompt building."""

import pytest

from argent.story import PromptBuilder, load_character


class TestPromptBuilder:
    """Test prompt generation without API calls."""

    def test_first_contact_prompt_contains_key(self):
        """Test that the key is embedded in the prompt."""
        persona = load_character("ember")
        builder = PromptBuilder()
        prompt = builder.build_first_contact_prompt(persona, "ABCD-1234-EFGH-5678")

        assert "ABCD-1234-EFGH-5678" in prompt

    def test_first_contact_prompt_has_do_not_rules(self):
        """Test that critical DO NOT rules are present."""
        persona = load_character("ember")
        builder = PromptBuilder()
        prompt = builder.build_first_contact_prompt(persona, "TEST-KEY")

        assert "Do NOT apologize" in prompt
        assert "Do NOT mention sending to the wrong person" in prompt
        assert "Do NOT explain what the key is for" in prompt

    def test_first_contact_prompt_has_context(self):
        """Test that first contact context is present."""
        persona = load_character("ember")
        builder = PromptBuilder()
        prompt = builder.build_first_contact_prompt(persona, "TEST-KEY")

        assert "Cipher" in prompt
        assert "DELIBERATE" in prompt or "deliberate" in prompt
        assert "NOT anxious or apologetic" in prompt or "not apologetic" in prompt.lower()

    def test_first_contact_prompt_has_example(self):
        """Test that example output is provided."""
        persona = load_character("ember")
        builder = PromptBuilder()
        prompt = builder.build_first_contact_prompt(persona, "TEST-KEY")

        assert "EXAMPLE OUTPUT" in prompt
        assert "XXXX-XXXX-XXXX-XXXX" in prompt  # Example key format
        assert "- E" in prompt  # Sign-off example

    def test_system_prompt_includes_trust(self):
        """Test that system prompt includes trust context."""
        persona = load_character("ember")
        builder = PromptBuilder()
        prompt = builder.build_system_prompt(persona, trust_score=50)

        assert "Trust" in prompt or "trust" in prompt

    def test_system_prompt_includes_knowledge(self):
        """Test that player knowledge is included when provided."""
        persona = load_character("ember")
        builder = PromptBuilder()
        prompt = builder.build_system_prompt(
            persona,
            player_knowledge=["Player mentioned Miro", "Player asked about Thursday"],
        )

        assert "Player mentioned Miro" in prompt
        assert "Player asked about Thursday" in prompt


class TestPersonaLoading:
    """Test persona registry and loading."""

    def test_ember_persona_exists(self):
        """Test that Ember persona can be loaded."""
        persona = load_character("ember")

        assert persona.agent_id == "ember"
        assert persona.display_name == "Ember"
        assert persona.channel == "email"

    def test_ember_has_avatar(self):
        """Test that Ember has an avatar defined."""
        persona = load_character("ember")

        assert persona.avatar == "ember.png"

    def test_ember_has_first_contact_config(self):
        """Test that Ember has first contact configuration."""
        persona = load_character("ember")

        assert persona.first_contact is not None
        assert persona.first_contact.situation is not None
        assert persona.first_contact.goal is not None
        assert len(persona.first_contact.tone_notes) > 0

    def test_unknown_agent_raises_error(self):
        """Test that loading unknown agent raises ValueError."""
        with pytest.raises(ValueError, match="Unknown agent"):
            load_character("nonexistent_agent")
