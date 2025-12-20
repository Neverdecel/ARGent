# Opening Week Timeline

This document defines the exact timing and triggers for the first week of player experience in ARGent.

---

## Day 1: First Contact

### Timeline

| Time | Event | Trigger | Channel |
|------|-------|---------|---------|
| T+0 | Key email sent | Player clicks "Start Game" | Email |
| T+2-4h | Ember first contact | Scheduled (or earlier if player replies to key) | Email |
| T+4-8h | Miro first contact | 2-4 hours after Ember's first message | Telegram |

### The Key Email

Sent immediately when player clicks "Start Game":

```
Subject: (empty)

It's ready. Use before Thursday.

a]@FyKbN2%nLp9$vR3xQ7mW
```

The key is unique per player, generated at registration.

### Ember's First Contact

Ember reaches out 2-4 hours after the key email, or immediately if the player replies to the key email first.

**Trigger conditions:**
- Default: 2-4 hour delay from key email
- Early trigger: Player replies to key email → Ember responds within 15-30 minutes

### Miro's First Contact

Miro contacts via Telegram 2-4 hours after Ember's first message.

**Trigger conditions:**
- Time-based: 2-4 hours after Ember's message timestamp
- Independent of player response to Ember

---

## Day 2-3: Conflicts Deepen

### Conversation Patterns

As the player engages with both agents, conflicts emerge through their responses:

| Topic | Ember Says | Miro Says |
|-------|------------|-----------|
| What the key is | "Old password, nothing important" | "Credentials to something valuable" |
| What's on dashboard | "Some files, not your concern" | "Evidence someone wants buried" |
| Thursday deadline | "Ignore it, doesn't matter" | "Someone expected delivery" |
| What to do | "Delete it, forget this happened" | "Explore it, know your leverage" |

### Trust Building

Trust is tracked per agent (-100 to 100, starts at 0):

**Trust increases when player:**
- Responds promptly
- Agrees with agent's perspective
- Shares information with them
- Shows empathy/understanding

**Trust decreases when player:**
- Ignores messages for extended periods
- Lies (if detectable)
- Shares confidential info with other agent
- Pushes too hard on uncomfortable topics

---

## Day 3: Dashboard Reveal

### Trigger Conditions

The dashboard URL/access hint is revealed when:
- **Time:** Day 3 or later
- **Trust:** Player has trust > 40 with at least one agent

### Who Reveals It

Whichever agent has higher trust reveals the dashboard access:

**If Miro has higher trust:**
> "I can show you where that key works. Consider it a gesture of good faith."

**If Ember has higher trust:**
> (Accidentally reveals when stressed) "You can't just... if you access the system, there are logs. Wait, forget I said that."

---

## Day 3-4: Thursday Deadline

### Real Timing

The "Thursday" deadline is real: **3-4 days after the player starts**.

### Agent Behavior

As the deadline approaches:

**Ember:** Becomes more anxious, messages increase in urgency
> "Please, you need to decide soon. After Thursday..."
> "I can't explain but it won't matter after that"

**Miro:** Notes the deadline, creates pressure
> "Thursday's coming. Whatever you're going to do, do it soon."
> "Deadlines exist for a reason. Someone was expecting delivery."

### After Thursday

If the deadline passes without player using the key:
- Story continues (key doesn't actually expire)
- Agents acknowledge the passed deadline
- New narrative tension: "What happens now that the window closed?"

---

## Edge Cases

### Single Agent Engagement

If player only engages with one agent:

1. **Ignored agent sends 1-2 follow-ups** (spaced 24h apart)
2. **Then goes quiet** - respects player choice
3. **Can re-enter later** if story events trigger it (e.g., player mentions them to other agent)

**Ember follow-up examples (if ignored):**
> "I haven't heard back. Please, this is important."
> "I understand if you don't trust me. But be careful who you do trust."

**Miro follow-up examples (if ignored):**
> "Still thinking it over? Take your time."
> (After 48h, no more follow-ups)

### Player Dormant (2+ Days Silent)

Tiered re-engagement approach:

**Stage 1: Escalation (Pre-deadline)**
- Agents increase urgency about Thursday deadline
- Messages reference time running out

**Stage 2: Gentle Re-engagement (Post-deadline)**
- After ~48h of silence: One agent sends concerned message
- Ember: "Are you okay? I haven't heard from you..."
- Miro: "Went quiet. Everything alright on your end?"

**Stage 3: Story Pause (Extended silence)**
- After 4-5 days: Agents wait
- When player returns, agents acknowledge the gap naturally
- Story resumes where it left off

---

## Summary

| Phase | Timing | Key Events |
|-------|--------|------------|
| Day 1 | T+0 to T+8h | Key email → Ember → Miro |
| Day 2-3 | Ongoing | Conflicts deepen, trust builds |
| Day 3 | Trust > 40 | Dashboard hint revealed |
| Day 3-4 | Real deadline | Thursday pressure peaks |
| Day 4+ | After deadline | Story continues, new tension |

---

## Implementation Notes

### Trigger Conditions (YAML)

```yaml
triggers:
  ember_first_contact:
    conditions:
      any:
        - event: "player_replied_to_key_email"
        - time_since: "key_email_sent"
          op: ">="
          value: "2h"
    action:
      agent: "ember"
      intent: "panicked_first_contact"

  miro_first_contact:
    conditions:
      - event: "ember_first_contact_sent"
      - time_since: "ember_first_contact_sent"
        op: ">="
        value: "2h"
    action:
      agent: "miro"
      intent: "smooth_first_contact"

  dashboard_reveal:
    conditions:
      - days_since: "game_start"
        op: ">="
        value: 3
      - any:
          - field: "trust.ember"
            op: ">"
            value: 40
          - field: "trust.miro"
            op: ">"
            value: 40
    action:
      agent: "highest_trust_agent"
      intent: "reveal_dashboard_access"
```

### Trust Calculation

| Action | Trust Change |
|--------|--------------|
| Player responds within 4h | +5 |
| Player agrees with agent | +10 |
| Player shares intel | +15 |
| Player ignores for 24h | -5 |
| Player lies (detected) | -20 |
| Player shares agent's secrets | -25 |
