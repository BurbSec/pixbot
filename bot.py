import io
import re
import os
from datetime import datetime, timezone

import aiohttp
import discord
from discord import app_commands
from PIL import Image
from github import Github, GithubException

import config

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)


def get_valid_locations():
    """Fetch valid location directories from GitHub. Falls back to config on error."""
    try:
        repo = Github(config.GITHUB_TOKEN).get_repo(config.GITHUB_REPO)
        contents = repo.get_contents(config.IMAGES_BASE_PATH, ref=config.GITHUB_BASE_BRANCH)
        locations = {item.name for item in contents if item.type == 'dir'}
        if locations:
            return locations
    except Exception as e:
        print(f'[pixbot] Could not fetch locations from GitHub: {e}')
    return set(config.FALLBACK_LOCATIONS)


def format_locations(locations):
    return ', '.join(sorted(locations))


def process_image(image_bytes):
    """Resize if above 4K, convert to WebP. Returns (webp_bytes, metadata dict)."""
    img = Image.open(io.BytesIO(image_bytes))

    # Convert palette/transparency modes for WebP compatibility
    if img.mode in ('P', 'RGBA'):
        img = img.convert('RGBA')
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    original_dims = (img.width, img.height)
    original_size = len(image_bytes)

    MAX_W, MAX_H = 3840, 2160
    if img.width > MAX_W or img.height > MAX_H:
        img.thumbnail((MAX_W, MAX_H), Image.LANCZOS)

    final_dims = (img.width, img.height)

    out = io.BytesIO()
    img.save(out, format='WEBP', quality=90)
    webp_bytes = out.getvalue()

    metadata = {
        'original_dims': original_dims,
        'original_size': original_size,
        'final_dims': final_dims,
        'final_size': len(webp_bytes),
    }
    return webp_bytes, metadata


def sanitize_filename(name):
    """Strip extension and replace non-alphanumeric chars with underscores."""
    base = os.path.splitext(name)[0]
    return re.sub(r'[^a-zA-Z0-9_-]', '_', base)


def format_size(nbytes):
    mb = nbytes / (1024 * 1024)
    return f'{mb:.1f} MB'


def build_pr_body(location, images_data, discord_msg):
    date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    message_link = (
        f'https://discord.com/channels/{discord_msg.guild.id}/'
        f'{discord_msg.channel.id}/{discord_msg.id}'
    )

    rows = []
    for filename, _webp_bytes, meta in images_data:
        orig_w, orig_h = meta['original_dims']
        fin_w, fin_h = meta['final_dims']
        rows.append(
            f'| {filename} | {orig_w}×{orig_h} | {fin_w}×{fin_h} '
            f'| {format_size(meta["final_size"])} |'
        )

    table = '\n'.join(rows)

    return (
        f'## New IRL Photo(s) — {location}\n\n'
        f'Submitted by **{discord_msg.author.display_name}** '
        f'in #{discord_msg.channel.name} on {date_str}\n\n'
        f'### Image Summary\n'
        f'| File | Original | Final | Size |\n'
        f'|------|----------|-------|------|\n'
        f'{table}\n\n'
        f'### Source\n'
        f'Discord message: {message_link}\n\n'
        f'---\n'
        f'*Submitted via pixbot*'
    )


def create_github_pr(location, images_data, discord_msg):
    """
    images_data: list of (filename, webp_bytes, metadata)
    Returns (pr_url, branch_name)
    """
    gh = Github(config.GITHUB_TOKEN)
    repo = gh.get_repo(config.GITHUB_REPO)

    base_sha = repo.get_branch(config.GITHUB_BASE_BRANCH).commit.sha
    branch_name = f'pixbot/{location}-{datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")}'
    repo.create_git_ref(ref=f'refs/heads/{branch_name}', sha=base_sha)

    for filename, webp_bytes, _meta in images_data:
        path = f'{config.IMAGES_BASE_PATH}/{location}/{filename}'
        repo.create_file(
            path=path,
            message=f'[pixbot] Add {filename} to {location}',
            content=webp_bytes,
            branch=branch_name,
        )

    pr_body = build_pr_body(location, images_data, discord_msg)
    pr = repo.create_pull(
        title=f'[pixbot] Add IRL photo(s) to {location}',
        body=pr_body,
        head=branch_name,
        base=config.GITHUB_BASE_BRANCH,
    )
    return pr.html_url, branch_name


def _has_allowed_role(interaction: discord.Interaction) -> bool:
    allowed = {r.lower() for r in config.ALLOWED_ROLES}
    return any(r.name.lower() in allowed for r in interaction.user.roles)


@tree.command(name='help', description='How to submit IRL meetup photos via pixbot')
async def help_command(interaction: discord.Interaction):
    if not _has_allowed_role(interaction):
        await interaction.response.send_message(
            'You do not have permission to use pixbot.', ephemeral=True
        )
        return

    valid_locations = get_valid_locations()

    embed = discord.Embed(
        title='pixbot — IRL Photo Submission',
        description=(
            'pixbot lets trusted members submit IRL meetup photos directly to the '
            'BurbSec website by opening a GitHub PR automatically.'
        ),
        color=discord.Color.blurple(),
    )

    embed.add_field(
        name='Who can use it',
        value=', '.join(f'`{r}`' for r in sorted(config.ALLOWED_ROLES)),
        inline=False,
    )

    embed.add_field(
        name='How to submit',
        value=(
            '1. Find a message that contains the photo(s) you want to submit.\n'
            '2. **Reply** to that message.\n'
            '3. In your reply, mention the bot and include a location:\n'
            '   > `@pixbot northwest`\n'
            '4. The bot will confirm once a PR has been opened.'
        ),
        inline=False,
    )

    embed.add_field(
        name='Valid locations',
        value=format_locations(valid_locations),
        inline=False,
    )

    embed.add_field(
        name='What happens to the image',
        value=(
            '• Downloaded from Discord\n'
            '• Resized to ≤ 3840×2160 if larger (aspect ratio preserved)\n'
            '• Converted to WebP at quality 90\n'
            '• Committed to `static/images/irl/<location>/` on a new branch\n'
            '• A pull request is opened on `BurbSec/burbsec.github.io`'
        ),
        inline=False,
    )

    embed.add_field(
        name='Multiple photos',
        value='All images attached to the replied-to message are bundled into a single PR.',
        inline=False,
    )

    embed.set_footer(text='pixbot — only replies to messages that contain images')

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.event
async def on_ready():
    await tree.sync()
    print(f'[pixbot] Logged in as {bot.user} (id={bot.user.id})')


@bot.event
async def on_message(message):
    # Ignore messages from bots (including self)
    if message.author.bot:
        return

    # Only respond when mentioned
    if bot.user not in message.mentions:
        return

    # Role check
    author_roles = [r.name.lower() for r in message.author.roles]
    allowed = [r.lower() for r in config.ALLOWED_ROLES]
    if not any(r in allowed for r in author_roles):
        return  # Silent — don't reveal bot existence to unauthorised users

    # Parse location from message content
    content = re.sub(r'<@!?\d+>', '', message.content).strip().lower()
    location = content.split()[0] if content else ''

    # Fetch valid locations fresh on each invocation
    valid_locations = get_valid_locations()

    if not location:
        await message.reply(
            f'Please specify a location. Valid locations: {format_locations(valid_locations)}'
        )
        return

    if location not in valid_locations:
        await message.reply(
            f'Unknown location `{location}`. Valid locations: {format_locations(valid_locations)}'
        )
        return

    # Must be a reply
    if not message.reference:
        await message.reply(
            'Please use this command as a reply to a message containing an image.'
        )
        return

    # Fetch the referenced message
    try:
        ref_msg = await message.channel.fetch_message(message.reference.message_id)
    except discord.NotFound:
        await message.reply('Could not find the referenced message.')
        return

    # Collect image attachments
    image_attachments = [
        a for a in ref_msg.attachments
        if a.content_type and a.content_type.startswith('image/')
    ]

    if not image_attachments:
        await message.reply('No images found in the referenced message.')
        return

    n = len(image_attachments)
    status_msg = await message.reply(f'Processing {n} image(s)…')

    # Download and process images
    images_data = []
    async with aiohttp.ClientSession() as session:
        for idx, attachment in enumerate(image_attachments):
            async with session.get(attachment.url) as resp:
                if resp.status != 200:
                    await status_msg.edit(
                        content=f'Failed to download image {attachment.filename} (HTTP {resp.status}).'
                    )
                    return
                raw_bytes = await resp.read()

            webp_bytes, meta = process_image(raw_bytes)

            base = sanitize_filename(attachment.filename)
            filename = f'{base}.webp' if n == 1 else f'{base}_{idx + 1}.webp'
            images_data.append((filename, webp_bytes, meta))

    # Create PR
    try:
        pr_url, branch_name = create_github_pr(location, images_data, message)
    except GithubException as e:
        await status_msg.edit(content=f'GitHub error: {e.data.get("message", str(e))}')
        return
    except Exception as e:
        await status_msg.edit(content=f'Unexpected error creating PR: {e}')
        return

    await status_msg.edit(
        content=(
            f'✅ PR created for **{location}**:\n'
            f'{pr_url}\n\n'
            f'{n} image(s) processed — branch `{branch_name}`'
        )
    )


if __name__ == '__main__':
    if not config.TOKEN:
        raise RuntimeError('DISCORD_BOT_TOKEN is not set.')
    if not config.GITHUB_TOKEN:
        raise RuntimeError('GITHUB_TOKEN is not set.')
    bot.run(config.TOKEN)
