# Web Inbox

A web-based communication interface for players who prefer not to use real email/SMS, or for development and demo purposes.

## Purpose

1. **Development** - Test agents and storyline without Mailgun/Twilio accounts
2. **Demos** - Show the game to testers or press without requiring real contact info
3. **Non-immersive mode** - Players who want to experience the story without giving real email/phone

## How It Works

### Player Communication Modes

Players choose their mode at registration:

- **Immersive** (default) - Real email and SMS via Mailgun/Twilio
- **Web-only** - All messages appear in the web inbox

### Registration Flow

1. Landing page (`/`) - Enter email
2. If new user, redirect to `/register` with email prefilled
3. Registration includes step progress indicator (Register → Verify → Start)
4. Web-only mode: Phone field hidden, verification auto-completed
5. After registration, web-only players go directly to `/start`
6. Timezone auto-detected from browser

### Inbox Structure

```
/inbox                           - Message list with title
/inbox/conversation/{session_id} - View conversation thread (with reply form)
```

Players can only reply within existing conversations - they cannot initiate new messages. This keeps the story agent-driven.

### Message Display

Messages are displayed with:
- Sender name
- Subject line (if present)
- Preview text
- Timestamp
- Unread indicator

## Technical Implementation

### Database

Added to `Player` model:
- `communication_mode` - 'immersive' or 'web_only'

`Message` model stores content directly for web-only mode:
- `channel` - 'email' or 'sms' (for display/filtering)
- `subject`, `content`, `html_content`, `sender_name`

### Services

- `WebInboxService` - Stores and retrieves messages from database
- `MessageDispatcher` - Routes messages based on player's communication mode

### Routes

Page routes in `api/inbox.py`:
- `GET /inbox` - Inbox list page
- `GET /inbox/conversation/{id}` - Conversation view with reply form

API routes:
- `GET /api/inbox/conversations` - List conversations
- `GET /api/inbox/messages/{id}` - Get single message
- `POST /api/inbox/messages/{id}/read` - Mark as read
- `POST /api/inbox/compose` - Send reply (within existing conversation)

### Configuration

```python
web_inbox_enabled: bool = True
allow_web_only_registration: bool = True
```

## Agent Integration

When sending messages to web-only players, agents use:

```python
await web_inbox_service.send_message(message, display_channel='email')  # or 'sms'
```

The `display_channel` parameter determines how the message appears in the inbox UI.
