import logging
import os
import subprocess

from dasa import utils


def main():
    utils.log_with_env('user_destroy_post', env=dict(os.environ))

    if 'username' not in os.environ:
        logging.error('Required environment variables missing, expecting: username')
        exit(1)

    username = os.environ.get('username')

    # Remove block_emails_scripts
    utils.file_ensure_da_user('/etc/virtual/blacklist_script_usernames', username, False)

    # Apply block_emails_all
    utils.file_ensure_da_user('/etc/virtual/blacklist_usernames', username, False)
