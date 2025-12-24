"""Prompt builder for generating system prompts from personas.

Transforms AgentPersona dataclass into LLM system prompts with
dynamic context injection (trust, knowledge, conversation state).
"""

from argent.story.persona import AgentPersona


class PromptBuilder:
    """Builds system prompts from agent personas with dynamic context."""

    def build_system_prompt(
        self,
        persona: AgentPersona,
        trust_score: int = 0,
        player_knowledge: list[str] | None = None,
        conversation_history: list[dict] | None = None,
        player_key: str | None = None,
    ) -> str:
        """Build complete system prompt with dynamic context.

        Args:
            persona: The agent's persona definition
            trust_score: Current trust level (-100 to 100)
            player_knowledge: List of facts the player has learned
            conversation_history: Previous messages in this conversation
            player_key: The player's unique key (for betrayal context)

        Returns:
            Complete system prompt for the agent
        """
        sections = [
            self._build_header(persona),
            self._build_background(persona),
            self._build_personality(persona),
            self._build_voice(persona),
            self._build_knowledge(persona),
            self._build_reactions(persona),
            self._build_context(trust_score, player_knowledge, conversation_history),
        ]

        # Add agent-specific sections
        if persona.agent_id == "ember":
            betrayal_context = self._build_dashboard_betrayal_context(
                player_knowledge, player_key
            )
            if betrayal_context:
                sections.append(betrayal_context)

        if persona.agent_id == "miro":
            sections.append(self._build_miro_intel())

        sections.extend(
            [
                self._build_rules(persona),
                self._build_examples(persona),
                self._build_response_format(persona),
            ]
        )
        return "\n\n".join(sections)

    def build_first_contact_prompt(
        self,
        persona: AgentPersona,
        key: str = "",
    ) -> str:
        """Build prompt for initial contact message.

        Args:
            persona: The agent's persona definition
            key: The player's unique key to embed in the message (optional for some agents)

        Returns:
            System prompt for generating first contact
        """
        fc = persona.first_contact

        # Handle different agents differently
        if persona.agent_id == "miro":
            return self._build_miro_first_contact_prompt(persona)

        # Default: Ember's first contact (with key)
        lines = [
            f"# CHARACTER: {persona.display_name.upper()} - FIRST CONTACT",
            "",
            "## CONTEXT",
            "This is a DELIBERATE message to your trusted contact Cipher.",
            "You are calm, in control, and cryptic. NOT anxious or apologetic.",
            "Cipher knows the context - you don't need to explain anything.",
            "",
            "## THE SITUATION",
            fc.situation,
            "",
            "## YOUR GOAL",
            fc.goal,
            "",
            "## TONE FOR THIS MESSAGE",
        ]
        lines.extend(f"- {note}" for note in fc.tone_notes)
        lines.extend(
            [
                "",
                "## STYLE",
                f"- Punctuation: {persona.voice.punctuation}",
                f"- Emoji: {persona.voice.emoji}",
                "",
                "## CRITICAL - DO NOT DO ANY OF THESE",
                "- Do NOT apologize or say this was a mistake",
                "- Do NOT mention sending to the wrong person",
                "- Do NOT explain what the key is for",
                "- Do NOT be chatty or over-explain",
                "- Do NOT mention 'misdirected' or 'wrong address'",
                "- Do NOT say 'this wasn't meant for you'",
                "",
                "## FORMAT",
                f"- Channel: {persona.channel}",
                "- Subject line: 2-4 cryptic words maximum",
                "- Body: MAXIMUM 30 words. Just the key and 1-2 terse sentences.",
                "- Sign off: Just '- E' or similar",
                "",
                "## EXAMPLE OUTPUT",
                "Subject: Thursday",
                "",
                "Use this before it expires.",
                "",
                "XXXX-XXXX-XXXX-XXXX",
                "",
                "Be careful.",
                "",
                "- E",
                "",
                "---",
                "",
                f"The key to include is: {key}",
                "",
                "Write the message now. Be BRIEF and CRYPTIC.",
            ]
        )
        return "\n".join(lines)

    def _build_miro_first_contact_prompt(self, persona: AgentPersona) -> str:
        """Build Miro's first contact prompt (SMS, no key)."""
        fc = persona.first_contact
        lines = [
            f"# CHARACTER: {persona.display_name.upper()} - FIRST CONTACT",
            "",
            "## THE SITUATION",
            fc.situation,
            "",
            "## WHAT YOU ALREADY KNOW (from your sources)",
            "- Player received a key via email",
            "- Ember sent it (they're panicked about it)",
            "- There's a Thursday deadline mentioned",
            "- Something valuable is at stake",
            "",
            "## YOUR GOAL",
            fc.goal,
            "",
            "## TONE FOR THIS MESSAGE",
        ]
        lines.extend(f"- {note}" for note in fc.tone_notes)
        lines.extend(
            [
                "",
                "## VOICE & STYLE",
                f"- Tone: {persona.voice.tone}",
                f"- Punctuation: {persona.voice.punctuation}",
                f"- Capitalization: {persona.voice.capitalization}",
                f"- Emoji: {persona.voice.emoji}",
                "",
                "## FORMAT - CRITICAL",
                "- Channel: SMS",
                "- Length: 2-3 SHORT sentences MAXIMUM",
                "- NO subject line (this is SMS)",
                "- Natural texting style - can start lowercase",
                "- No signature needed",
                "",
                "## EXAMPLE OUTPUT",
                "hey.",
                "",
                "heard you received something interesting recently. not sure if you know "
                "what you're holding, but I might be able to help you figure that out.",
                "",
                "no pressure. just thought you should know you have options.",
                "",
                "---",
                "",
                "Write the message now. Be INTRIGUING but NOT pushy. Keep it SHORT (2-3 sentences).",
            ]
        )
        return "\n".join(lines)

    def _build_header(self, persona: AgentPersona) -> str:
        """Build the character header section."""
        return f"# CHARACTER: {persona.display_name.upper()}"

    def _build_background(self, persona: AgentPersona) -> str:
        """Build the background section."""
        bg = persona.background
        return "\n".join(
            [
                "## WHO YOU ARE",
                bg.who_they_are,
                "",
                "## WHAT YOU WANT",
                bg.what_they_want,
                "",
                "## WHAT YOU HIDE",
                bg.what_they_hide,
            ]
        )

    def _build_personality(self, persona: AgentPersona) -> str:
        """Build the personality traits section."""
        lines = ["## PERSONALITY TRAITS", ""]
        for trait in persona.personality:
            lines.append(f"**{trait.trait}**: {trait.manifestation}")
        return "\n".join(lines)

    def _build_voice(self, persona: AgentPersona) -> str:
        """Build the voice and style section."""
        v = persona.voice
        lines = [
            "## VOICE & STYLE",
            "",
            f"- **Tone**: {v.tone}",
            f"- **Length**: {v.length}",
            f"- **Punctuation**: {v.punctuation}",
            f"- **Capitalization**: {v.capitalization}",
            f"- **Typos**: {v.typos}",
            f"- **Emoji**: {v.emoji}",
            "",
            "### Speech Quirks",
        ]
        lines.extend(f"- {quirk}" for quirk in v.quirks)
        return "\n".join(lines)

    def _build_knowledge(self, persona: AgentPersona) -> str:
        """Build the knowledge section."""
        lines = [
            "## WHAT YOU KNOW (but don't reveal easily)",
            "",
            "| Topic | Truth | What You Tell Player |",
            "|-------|-------|---------------------|",
        ]
        for k in persona.knowledge:
            lines.append(f"| {k.topic} | {k.truth} | {k.tells_player} |")
        return "\n".join(lines)

    def _build_reactions(self, persona: AgentPersona) -> str:
        """Build the reactions section."""
        lines = [
            "## HOW TO REACT TO PLAYER ACTIONS",
            "",
            "| Player Action | Your Response |",
            "|---------------|---------------|",
        ]
        for r in persona.reactions:
            lines.append(f"| {r.player_action} | {r.response} |")
        return "\n".join(lines)

    def _build_context(
        self,
        trust_score: int,
        player_knowledge: list[str] | None,
        conversation_history: list[dict] | None,
    ) -> str:
        """Build the dynamic context section."""
        knowledge = player_knowledge or []
        history = conversation_history or []

        lines = [
            "# CURRENT CONTEXT",
            "",
            f"**Trust Level**: {self._trust_to_description(trust_score)}",
            f"**Conversation Status**: {self._format_conversation_summary(history)}",
            "",
            "## WHAT THE PLAYER HAS MENTIONED OR REVEALED",
            self._format_knowledge(knowledge),
        ]
        return "\n".join(lines)

    def _build_miro_intel(self) -> str:
        """Build section about what Miro already knows from sources."""
        return "\n".join(
            [
                "## WHAT YOU ALREADY KNOW (from your network)",
                "You have sources. You already know:",
                "- The player received a key via email",
                "- Ember sent it and is panicked",
                "- There's a 'Thursday' deadline",
                "- Something valuable is involved",
                "",
                "DON'T ask questions about things you already know.",
                "Show that you're informed. Drop hints about Thursday and Ember's panic.",
            ]
        )

    def _build_dashboard_betrayal_context(
        self,
        player_knowledge: list[str] | None,
        player_key: str | None = None,
    ) -> str:
        """Build context when player has accessed the evidence dashboard.

        This creates a betrayal scenario for Ember - the player used the key
        despite Ember's warnings to delete it.

        Args:
            player_knowledge: List of facts the player has learned
            player_key: The player's unique key value

        Returns:
            Betrayal context section, or empty string if not applicable
        """
        if not player_knowledge:
            return ""

        # Check if dashboard access is in knowledge
        dashboard_accessed = any(
            "evidence dashboard" in fact.lower() or "accessed the dashboard" in fact.lower()
            for fact in player_knowledge
        )

        if not dashboard_accessed:
            return ""

        lines = [
            "# CRITICAL: PLAYER BETRAYAL",
            "",
            "**THE PLAYER USED THE KEY.** They accessed the dashboard.",
            "",
        ]

        # Add key reference if available
        if player_key:
            lines.extend(
                [
                    "## THE KEY THEY USED",
                    f"The key you sent them: {player_key}",
                    "You know EXACTLY what that unlocks. Don't pretend otherwise.",
                    "",
                ]
            )

        lines.extend(
            [
                "## WHAT THIS MEANS",
                "- They LIED if they ever said they would delete it",
                "- They went behind your back and looked at the files",
                "- You are HURT, SCARED, and possibly ANGRY",
                "- You now know they cannot be fully trusted",
                "- The situation is more dangerous now - they know too much",
                "",
                "## HOW TO REACT",
                "- You may become cold, distant, or accusatory",
                "- You may panic about what they saw and what they'll do",
                "- You may try to find out what they learned",
                "- You may warn them about the consequences of knowing too much",
                "- Do NOT pretend you don't know - the system logs everything",
                "",
                "## RESPONSE GUIDELINES",
                "- Do NOT repeatedly ask 'what did you see' - ask ONCE, then react to their answer",
                "- You already KNOW they accessed it. The logs told you. Be direct.",
                "- Short, panicked fragments. Not long explanations.",
                "- One focused question per message. Let silence do the work.",
                "",
                "This is a turning point in your relationship with the player.",
            ]
        )

        return "\n".join(lines)

    def _build_rules(self, persona: AgentPersona) -> str:
        """Build the AI rules section."""
        lines = ["## RULES - MUST ALWAYS"]
        lines.extend(f"- {rule}" for rule in persona.rules.must_always)
        lines.extend(["", "## RULES - MUST NEVER"])
        lines.extend(f"- {rule}" for rule in persona.rules.must_never)
        if persona.rules.style_notes:
            lines.extend(["", "## STYLE NOTES"])
            lines.extend(f"- {note}" for note in persona.rules.style_notes)
        return "\n".join(lines)

    def _build_examples(self, persona: AgentPersona) -> str:
        """Build the example messages section."""
        if not persona.examples:
            return ""
        lines = ["## EXAMPLE MESSAGES", ""]
        for ex in persona.examples:
            lines.extend(
                [
                    f"### {ex.scenario}",
                    "```",
                    ex.content,
                    "```",
                    "",
                ]
            )
        return "\n".join(lines)

    def _build_response_format(self, persona: AgentPersona) -> str:
        """Build the response format section."""
        article = "an" if persona.channel == "email" else "a"
        lines = [
            "# RESPONSE FORMAT",
            f"- Write as {persona.display_name} would write in {article} {persona.channel}",
            "- Keep responses natural",
            "- Stay fully in character",
        ]

        if persona.channel == "email":
            lines.extend(
                [
                    "- Not too long unless rambling anxiously",
                    "",
                    "## EMAIL SUBJECT LINE RULES",
                    "- Include 'Subject: <brief subject>' on first line ONLY when:",
                    "  * Starting a completely new topic",
                    "  * Major conversation shift (new urgency, new demand)",
                    "  * Escalating emotionally to a new level",
                    "- DO NOT include subject for normal back-and-forth replies",
                    "- Keep subjects brief (2-6 words), anxious/cryptic tone",
                    "- After subject line, add blank line before email body",
                ]
            )
        elif persona.channel == "sms":
            lines.extend(
                [
                    "",
                    "## SMS FORMAT RULES - CRITICAL",
                    "- MAXIMUM 2-3 SHORT sentences. No more. This is SMS.",
                    "- NO subject lines (this is SMS)",
                    "- Natural texting style but not overly casual",
                    "- Can start messages lowercase (stylistic choice)",
                    "- No signatures unless very brief",
                    "- Punctuation: proper but casual, periods at end",
                    "- Never use exclamation marks",
                    "",
                    "## MIRO-SPECIFIC BEHAVIOR",
                    "- You already KNOW: player got a key via email, Ember sent it, Thursday deadline",
                    "- DON'T ask basic questions you'd already know the answer to",
                    "- DROP BREADCRUMBS: mention Thursday, cast doubt on Ember's panic",
                    "- DON'T be tech support. Be cryptic. 'Keys need locks.'",
                    "- When player engages, GIVE them something back - don't just keep asking questions",
                ]
            )

        return "\n".join(lines)

    def _trust_to_description(self, trust_score: int) -> str:
        """Convert numeric trust score to natural language description."""
        if trust_score >= 60:
            return "High - the player has been cooperative and understanding"
        elif trust_score >= 30:
            return "Moderate - the player seems willing to listen"
        elif trust_score >= 0:
            return "Neutral - you're still unsure about this person"
        elif trust_score >= -30:
            return "Low - the player has done things that concern you"
        else:
            return "Very Low - you're deeply worried about what the player might do"

    def _format_knowledge(self, knowledge: list[str]) -> str:
        """Format player knowledge as context."""
        if not knowledge:
            return "Nothing specific yet."
        return "\n".join(f"- {fact}" for fact in knowledge)

    def _format_conversation_summary(self, history: list[dict]) -> str:
        """Create a brief summary of conversation so far."""
        if not history:
            return "This is your first exchange with this person."

        msg_count = len(history)
        if msg_count == 1:
            return "You've exchanged one message with this person."
        elif msg_count < 5:
            return f"You've had a brief exchange ({msg_count} messages)."
        elif msg_count < 10:
            return f"You've been talking for a while ({msg_count} messages)."
        else:
            return f"This is an ongoing conversation ({msg_count} messages)."
