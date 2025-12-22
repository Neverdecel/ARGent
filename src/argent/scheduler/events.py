"""Story event definitions and registry."""

from dataclasses import dataclass
from enum import Enum


class EventTrigger(str, Enum):
    """What triggers this event."""

    GAME_START = "game_start"
    TIME_AFTER_EVENT = "time_after_event"
    PLAYER_ACTION = "player_action"


@dataclass(frozen=True)
class DelayRange:
    """Delay range for immersive mode (in seconds)."""

    min_seconds: int
    max_seconds: int

    @classmethod
    def hours(cls, min_hours: float, max_hours: float) -> "DelayRange":
        """Create delay range from hours."""
        return cls(
            min_seconds=int(min_hours * 3600),
            max_seconds=int(max_hours * 3600),
        )

    @classmethod
    def minutes(cls, min_minutes: float, max_minutes: float) -> "DelayRange":
        """Create delay range from minutes."""
        return cls(
            min_seconds=int(min_minutes * 60),
            max_seconds=int(max_minutes * 60),
        )

    @classmethod
    def immediate(cls) -> "DelayRange":
        """No delay."""
        return cls(min_seconds=0, max_seconds=0)


@dataclass(frozen=True)
class StoryEvent:
    """A scheduled story event definition."""

    event_id: str
    handler: str  # Dotted path to handler function
    trigger: EventTrigger
    delay: DelayRange
    after_event: str | None = None  # For TIME_AFTER_EVENT trigger
    description: str = ""
    agent_id: str | None = None
    channel: str | None = None


# Story Event Registry
STORY_EVENTS: dict[str, StoryEvent] = {
    "ember_first_contact": StoryEvent(
        event_id="ember_first_contact",
        handler="argent.scheduler.handlers.send_ember_first_contact",
        trigger=EventTrigger.GAME_START,
        delay=DelayRange.immediate(),
        description="Ember sends the cryptic key email",
        agent_id="ember",
        channel="email",
    ),
    "miro_first_contact": StoryEvent(
        event_id="miro_first_contact",
        handler="argent.scheduler.handlers.send_miro_first_contact",
        trigger=EventTrigger.TIME_AFTER_EVENT,
        after_event="ember_first_contact",
        delay=DelayRange.hours(4, 6),
        description="Miro reaches out via SMS",
        agent_id="miro",
        channel="sms",
    ),
}


def get_event(event_id: str) -> StoryEvent:
    """Get a story event by ID."""
    if event_id not in STORY_EVENTS:
        raise ValueError(f"Unknown story event: {event_id}")
    return STORY_EVENTS[event_id]


def get_events_triggered_by(trigger: EventTrigger) -> list[StoryEvent]:
    """Get all events with a specific trigger type."""
    return [e for e in STORY_EVENTS.values() if e.trigger == trigger]


def get_events_after(event_id: str) -> list[StoryEvent]:
    """Get all events that should fire after the given event."""
    return [
        e
        for e in STORY_EVENTS.values()
        if e.trigger == EventTrigger.TIME_AFTER_EVENT and e.after_event == event_id
    ]
