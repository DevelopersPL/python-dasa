import os
from dasa import ciapi
from dasa.config import config
from dasa import utils


def main():
    utils.log_with_env('domain_pointer_create_pre', env=dict(os.environ))

    s = ciapi.get_session()
    r = s.post(config.get('DEFAULT', 'api_base_url') + 'system/directadmin/domain_pointer_create_pre',
               json=dict(os.environ),
               timeout=config.getint('DEFAULT', 'api_timeout'))

    if r.status_code == 404:
        print(r.json().get('message'))
        exit(0)

    if r.status_code != 200:
        print(r.json().get('message'))
        exit(1)
