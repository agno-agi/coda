# Connecting Coda to Slack

Coda works standalone via CLI, but it's designed to live in Slack where your team already asks questions. Each Slack thread becomes a session with its own conversation context.

## Prerequisites

- A Slack workspace with admin privileges
- Coda running locally or deployed (see README)
- ngrok (for local development only)

## Step 1: Create a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click **Create New App**
3. Select **From scratch**
4. Enter an app name (e.g. `Coda`) and select your workspace
5. Click **Create App**

## Step 2: Configure OAuth & Permissions

1. Navigate to **OAuth & Permissions** in your Slack App settings
2. Under **Scopes**, click **Add an OAuth Scope**
3. Add the following Bot Token Scopes:

| Scope | Why |
|-------|-----|
| `app_mention` | Respond when mentioned in channels |
| `chat:write` | Send messages |
| `chat:write.customize` | Send messages with custom username/icon |
| `chat:write.public` | Send messages to channels Coda hasn't joined |
| `im:history` | Read DM history for context |
| `im:read` | View DM metadata |
| `im:write` | Send DMs |

4. Scroll to the top and click **Install to Workspace**
5. Click **Allow** to authorize the app

## Step 3: Set Environment Variables

Copy the credentials into your `.env` file:

```bash
SLACK_TOKEN="xoxb-your-bot-user-token"       # OAuth & Permissions → Bot User OAuth Token
SLACK_SIGNING_SECRET="your-signing-secret"    # Basic Information → App Credentials → Signing Secret
```

## Step 4: Set Up the Webhook

### Local development (ngrok)

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

### Connect to Slack

1. In your Slack App settings, go to **Event Subscriptions**
2. Toggle **Enable Events** on
3. Set the Request URL to: `https://your-url/slack/events`
4. Wait for Slack to verify the endpoint (Coda must be running)

## Step 5: Configure Event Subscriptions

Under **Subscribe to bot events**, click **Add Bot User Event** and add:

| Event | Why |
|-------|-----|
| `app_mention` | Respond to @Coda mentions in channels |
| `message.im` | Respond to direct messages |
| `message.channels` | Listen in public channels (optional) |
| `message.groups` | Listen in private channels (optional) |

Click **Save Changes**.

## Step 6: Enable App Home

1. Go to **App Home** in your Slack App settings
2. Under **Show Tabs**, enable **Messages Tab**
3. Check **Allow users to send Slash commands and messages from the messages tab**
4. Save changes

## Step 7: Reinstall

1. Go to **Install App** in your Slack App settings
2. Click **Reinstall to Workspace**
3. Authorize the app with the new permissions

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
