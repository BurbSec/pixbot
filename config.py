import os

TOKEN = os.environ.get('PIXBOT_DISCORD_TOKEN')

# GitHub App auth (preferred)
GITHUB_APP_ID = os.environ.get('GITHUB_APP_ID')
GITHUB_APP_PRIVATE_KEY_PATH = os.environ.get('GITHUB_APP_PRIVATE_KEY_PATH')

# Fallback: personal access token
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')

ALLOWED_ROLES = ['moderators', 'Meetup Hosts']

GITHUB_REPO = 'BurbSec/burbsec.github.io'
IMAGES_BASE_PATH = 'static/images/irl'
GITHUB_BASE_BRANCH = 'main'

# Fallback if GitHub API unavailable at startup
FALLBACK_LOCATIONS = [
    'cigarsec', 'east', 'galway', 'lasvegas', 'mpls',
    'north', 'northwest', 'prime', 'south', 'southeast', 'west'
]
