import os
import subprocess
import dasa.utils as utils


def main():
    if 'username' not in os.environ:
        print('Required environment variables missing, expecting: username')
        exit(1)

    utils.log_with_env('user_destroy_post', env=dict(os.environ))

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

    # Run CloudLinux hooks
    subprocess.check_call(['/usr/bin/da-removesudoer', username, 'cagefs_user'])
    subprocess.check_call('/usr/share/cagefs-plugins/hooks/directadmin/user_destroy_post.sh')
    subprocess.call(['/usr/bin/da_remove_admin', username])  # ignore result
