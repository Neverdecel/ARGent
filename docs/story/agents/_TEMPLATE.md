# Agent Template

This template defines the structure for all agent profiles. Copy this file and fill in the sections.

---

## Identity

```yaml
handle: ""           # Display name
channel: ""          # email | telegram
status: ""           # active | future | inactive
introduced_by: ""    # How player meets them (onboarding | agent:name | story_event)
```

---

## Avatar

Visual presentation for profile pictures and mental image.

```yaml
style: ""            # photo | illustration | abstract | symbol
gender_presentation: ""  # ambiguous | masculine | feminine
age_impression: ""   # 20s | 30s | 40s | ageless
```

**Visual Description:**
(2-3 sentences describing what the avatar looks like)

**Mood/Aesthetic:**
(What feeling should the image convey)

**References:**
(Optional: similar vibes from film/photography)

**Technical Notes:**
- Telegram: 512x512px profile photo
- Email: Can reference in "From" name styling

---

## Character Inspiration

| Reference | What We Take |
|-----------|--------------|
| Film/Character | Specific trait or energy |

**The Blend:** One sentence describing the combined persona.

---

## Background

**Who they are:** (2-3 sentences, the truth)

**What they want:** (Primary motivation)

**What they hide:** (What they don't tell the player)

---

## Personality

| Trait | Manifestation |
|-------|---------------|
| Trait name | How it shows in messages |

---

## Voice & Style

### Tone
(One sentence describing overall communication tone)

### Message Patterns

| Aspect | Pattern |
|--------|---------|
| Length | short / medium / long / variable |
| Punctuation | (specific habits) |
| Capitalization | (specific habits) |
| Typos | (when/how they occur) |
| Emoji | (usage pattern) |

### Speech Quirks
- (Bullet list of specific verbal habits)

---

## Knowledge

### What They Know

| Topic | Truth | Tells Player |
|-------|-------|--------------|
| Topic | What's true | What they say |

### System Access

| Capability | Yes/No | Notes |
|------------|--------|-------|
| Can see if key is used | | |
| Can verify player claims | | |
| Has access to dashboard | | |

---

## Behavior

### Response Timing

| Context | Delay |
|---------|-------|
| Normal | |
| Urgent | |
| Player ghosting | |

### Reactions

| Player Action | Response |
|---------------|----------|
| Action | How agent reacts |

---

## Trust Dynamics

### Building Trust
- (What actions increase trust)

### Breaking Trust
- (What actions decrease trust)

---

## Example Messages

### First Contact
```
(Example message)
```

### Typical Exchange
```
(Example message)
```

### Under Pressure
```
(Example message)
```

---

## AI Generation Rules

### Must Always
- (Rules to follow)

### Must Never
- (Rules to avoid)

### Style Notes
```
(Notes for AI system prompt)
```
