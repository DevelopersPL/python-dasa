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

    # Apply limit_emails
    try:
        os.remove('/etc/virtual/limit_' + username)
    except OSError:
        pass

    try:
        # Run CloudLinux hooks
        subprocess.check_call(['/usr/bin/da-removesudoer', username, 'cagefs_user'])
        subprocess.check_call('/usr/share/cagefs-plugins/hooks/directadmin/user_destroy_post.sh')
        subprocess.call(['/usr/bin/da_remove_admin', username])  # ignore result
    except subprocess.CalledProcessError as e:
        utils.plog(logging.ERROR, e, exc_info=True)
        logging.error(e)
