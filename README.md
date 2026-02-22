# pixbot

Discord bot for BurbSec that lets trusted members submit IRL meetup photos to the [burbsec.github.io](https://burbsec.github.io) site via GitHub PR.

## How it works

1. A user with an allowed role replies to a Discord message containing photo(s)
2. They mention the bot with a location: `@pixbot northwest`
3. pixbot downloads the image(s), resizes to ≤ 3840×2160 if needed, and converts to WebP
4. A pull request is opened on `BurbSec/burbsec.github.io` adding the file(s) to `static/images/irl/<location>/`

## Commands

| Command | Description |
|---------|-------------|
| `@pixbot <location>` | Reply to a message with images to submit them |
| `/help` | Show usage instructions and valid locations |

Both require the `moderators` or `meetup-hosts` role.

## Setup

### Prerequisites

- Python 3.10+
- A Discord bot token with the **Message Content** intent enabled
- A GitHub personal access token with `repo` scope on `BurbSec/burbsec.github.io`

### Install

```bash
pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
```

Edit `.env`:

```
DISCORD_BOT_TOKEN=your_discord_bot_token_here
GITHUB_TOKEN=your_github_pat_here
```

### Run

```bash
python bot.py
```

## Configuration

All tunables are in `config.py`:

| Variable | Default | Description |
|----------|---------|-------------|
| `ALLOWED_ROLES` | `['moderators', 'meetup-hosts']` | Discord role names that can use the bot |
| `GITHUB_REPO` | `BurbSec/burbsec.github.io` | Target repository |
| `IMAGES_BASE_PATH` | `static/images/irl` | Base path for images in the repo |
| `GITHUB_BASE_BRANCH` | `main` | Branch PRs are opened against |
| `FALLBACK_LOCATIONS` | *(list)* | Used if GitHub is unreachable at startup |

Valid locations are fetched live from the repo on each submission. The fallback list is only used if the GitHub API is unavailable.

## Discord Bot Setup

When creating the bot in the [Discord Developer Portal](https://discord.com/developers/applications):

- Under **Bot → Privileged Gateway Intents**, enable **Message Content Intent**
- Under **OAuth2 → URL Generator**, grant the `bot` and `applications.commands` scopes
- Required bot permissions: `Read Messages/View Channels`, `Send Messages`, `Read Message History`

## Image processing

- Accepts any image format Discord supports (JPEG, PNG, GIF, HEIC, etc.)
- Images larger than 3840×2160 are scaled down proportionally using Lanczos resampling
- All images are saved as WebP at quality 90
- Multiple images in a single message are bundled into one PR on one branch

## Branch naming

Branches follow the pattern `pixbot/<location>-YYYYMMDD-HHMMSS` (UTC), e.g. `pixbot/northwest-20260221-183042`.
