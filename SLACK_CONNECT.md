# Connecting Coda to Slack

Coda is designed to live in Slack. Each Slack thread becomes a session with its own conversation context.

## Prerequisites

- A Slack workspace with admin privileges
- Coda running locally or deployed (see README)
- ngrok (for local development only)

## Step 1: Create a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click **Create New App**
3. Select **From a manifest**
4. Select your workspace
5. Choose **JSON** and paste the manifest below
6. Replace `https://your-url` with your actual URL (see Step 3) [ <--- NOTE - you need to ]
7. Click **Create**

```json
{
    "display_information": {
        "name": "Coda",
        "description": "A code companion that lives in Slack.",
        "background_color": "#171717"
    },
    "features": {
        "app_home": {
            "home_tab_enabled": false,
            "messages_tab_enabled": true,
            "messages_tab_read_only_enabled": false
        },
        "bot_user": {
            "display_name": "Coda",
            "always_online": true
        }
    },
    "oauth_config": {
        "scopes": {
            "bot": [
                "app_mentions:read",
                "channels:history",
                "channels:read",
                "chat:write",
                "chat:write.customize",
                "chat:write.public",
                "groups:history",
                "im:history",
                "im:read",
                "im:write"
            ]
        }
    },
    "settings": {
        "event_subscriptions": {
            "request_url": "https://your-url/slack/events",
            "bot_events": [
                "app_mention",
                "message.channels",
                "message.groups",
                "message.im"
            ]
        },
        "org_deploy_enabled": false,
        "socket_mode_enabled": false,
        "is_hosted": false,
        "token_rotation_enabled": false
    }
}
```

The manifest configures all scopes, events, and app home settings automatically.

## Step 2: Install to Workspace

After creating the app:

1. Go to **Install App** in the sidebar
2. Click **Install to Workspace**
3. Click **Allow** to authorize

## Step 3: Set Up Your URL

### Local development

1. Start Coda:

```bash
docker compose up -d --build
```

2. Expose your local server via ngrok:
```bash
ngrok http 8000
```

3. Copy the `https://` URL from ngrok output

### Production

Use your deployed URL (e.g. `https://coda.yourdomain.com`).

### Update the Request URL

If you used a placeholder URL in the manifest:

1. Go to **Event Subscriptions** in your Slack App settings
2. Update the Request URL to: `https://your-actual-url/slack/events`
3. Wait for Slack to verify the endpoint (Coda must be running)

## Step 4: Set Environment Variables

Copy the credentials into your `.env` file:
```bash
# Bot User OAuth Token (OAuth & Permissions page)
SLACK_TOKEN="xoxb-***"

# Signing Secret (Basic Information → App Credentials)
SLACK_SIGNING_SECRET="***"
```

Restart Coda to pick up the new variables:
```bash
docker compose up -d
```

## Verify

In Slack, try:
```
@Coda hi
@Coda what repos are available?
```

Each thread maintains its own conversation context automatically.

## How It Works

Coda uses [Agno's Slack interface](https://docs.agno.com/deploy/interfaces/slack/overview). The integration is configured in `app/main.py`:
```python
from agno.os.interfaces.slack import Slack

Slack(
    team=coda,
    token=SLACK_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET,
)
```

Thread timestamps are used as session IDs, so each Slack thread is an independent conversation with full history.