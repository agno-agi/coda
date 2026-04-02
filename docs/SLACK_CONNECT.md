# Connecting Coda to Slack

Coda is designed to live in Slack. Each Slack thread becomes a session with its own conversation context.

## Prerequisites

- Coda running locally or deployed (see README step 4)
- A Slack workspace with admin privileges
- [ngrok](https://ngrok.com) installed (for local development only)

## Step 1: Get your URL

You need a public URL that Slack can reach. If you're running locally, use ngrok to expose your local server.

### Local development

Expose your local server via ngrok:

```bash
ngrok http 8000
```

Copy the `https://` URL from the output — you'll paste it into the manifest next.

### Production

Use your deployed URL (e.g. `https://coda.yourdomain.com`).

## Step 2: Create a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click **Create New App**
3. Select **From an app manifest**
4. Select your workspace
5. Choose **JSON** and paste the manifest below — replace `https://your-url` with the URL from Step 1
6. Click **Create**

```json
{
    "display_information": {
        "name": "Coda",
        "description": "A code companion that lives in Slack.",
        "background_color": "#000000"
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
                "assistant:write",
                "channels:history",
                "channels:read",
                "chat:write",
                "chat:write.customize",
                "chat:write.public",
                "files:read",
                "files:write",
                "groups:history",
                "im:history",
                "im:read",
                "im:write",
                "search:read.public",
                "search:read.files",
                "search:read.users",
                "users:read",
                "users:read.email"
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

## Step 3: Install to Workspace

After creating the app:

1. Go to **Install App** in the sidebar
2. Click **Install to Workspace**
3. Click **Allow** to authorize

Copy the **Bot User OAuth Token** shown after install — you'll need it next.

## Step 4: Set Environment Variables

Copy the credentials into your `.env` file:

```bash
# Bot User OAuth Token (from Step 3)
SLACK_TOKEN="xoxb-***"

# Signing Secret (Basic Information → App Credentials)
SLACK_SIGNING_SECRET="***"
```

Restart Coda to pick up the Slack credentials:

```bash
docker compose up -d
```

## Verify

There are two ways to talk to Coda in Slack:

**Direct message** — find Coda under **Apps** in the Slack sidebar and message it directly, just like any teammate:

```
hi
what repos are available?
```

**In a channel** — invite Coda first, then mention it in any message:

```
/invite @Coda
@Coda walk me through the auth flow
```

Each thread maintains its own conversation context automatically. Follow-up messages in the same thread don't need to mention @Coda again.

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