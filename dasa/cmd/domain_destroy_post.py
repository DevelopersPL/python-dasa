import os
import subprocess

from dasa import ciapi
from dasa.config import config
from dasa import utils


def main():
    utils.log_with_env('domain_destroy_post', env=dict(os.environ))

    # Run CloudLinux hooks
    subprocess.check_call([
        '/opt/alt/python27/lib/python2.7/site-packages/clcommon/cpapi/helpers/directadmin_cache.py',
        'update',
        '--user=' + os.environ['username']
    ])

    s = ciapi.get_session()
    r = s.post(config.get('DEFAULT', 'api_base_url') + 'system/directadmin/domain_destroy_post',
               json=dict(os.environ),
               timeout=config.getint('DEFAULT', 'api_timeout'))

    if r.status_code == 404:
        print(r.json().get('message'))
        exit(0)

    if r.status_code != 200:
        print(r.json().get('message'))
        exit(1)
