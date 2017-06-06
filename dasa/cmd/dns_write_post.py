import os
from dasa import ciapi
from dasa.config import config
from dasa import utils


def main():
    if 'DOMAIN' not in os.environ:
        print('Required environment variables missing, expecting: DOMAIN')
        exit(1)

    utils.log_with_env('dns_write_post', env=dict(os.environ))

    s = ciapi.get_session()
    r = s.post(config.get('DEFAULT', 'api_base_url') + 'system/directadmin/dns_write_post',
           json=dict(os.environ),
           timeout=config.getint('DEFAULT', 'api_timeout'))

    if r.status_code != 200:
        print(r.json().get('message'))
        exit(1)
