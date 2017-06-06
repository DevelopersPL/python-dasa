import os
import subprocess
from dasa import ciapi
from dasa.config import config
from dasa import utils


def main():
    utils.log_with_env('user_restore_post', env=dict(os.environ))

    # Run CloudLinux hooks
    subprocess.call('/usr/share/cagefs-plugins/hooks/directadmin/user_restore_post.sh')  # ignore result

    # Report to CIAPI
    s = ciapi.get_session()
    r = s.post(config.get('DEFAULT', 'api_base_url') + 'system/directadmin/user_restore_post',
               json=dict(os.environ),
               timeout=config.getint('DEFAULT', 'api_timeout'))

    if r.status_code == 404:
        print(r.json().get('message'))
        exit(0)

    if r.status_code != 200:
        print(r.json().get('message'))
        exit(1)
