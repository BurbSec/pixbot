import os

TOKEN = os.environ.get('DISCORD_BOT_TOKEN')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')

ALLOWED_ROLES = ['moderators', 'meetup-hosts']

GITHUB_REPO = 'BurbSec/burbsec.github.io'
IMAGES_BASE_PATH = 'static/images/irl'
GITHUB_BASE_BRANCH = 'main'

# Fallback if GitHub API unavailable at startup
FALLBACK_LOCATIONS = [
    'cigarsec', 'east', 'galway', 'lasvegas', 'mpls',
    'north', 'northwest', 'prime', 'south', 'southeast', 'west'
]
