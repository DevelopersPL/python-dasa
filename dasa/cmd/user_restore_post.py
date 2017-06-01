import os
import subprocess
from dasa import ciapi
from dasa.config import config


def main():
    # Run CloudLinux hooks
    subprocess.check_call('/usr/share/cagefs-plugins/hooks/directadmin/user_restore_post.sh')

    # Report to CIAPI
    s = ciapi.get_session()
    s.post(config.get('DEFAULT', 'api_base_url') + 'system/directadmin/user_restore_post',
           json=dict(os.environ),
           timeout=config.getint('DEFAULT', 'api_timeout'))

    if s.status_code == 404:
        print(s.json().get('message'))
        exit(0)

    if s.status_code != 200:
        print(s.json().get('message'))
        exit(1)
