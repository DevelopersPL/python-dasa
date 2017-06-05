import os
from dasa import ciapi
from dasa.config import config


def main():
    if 'DOMAIN' not in os.environ:
        print('Required environment variables missing, expecting: DOMAIN')
        exit(1)

    s = ciapi.get_session()
    r = s.post(config.get('DEFAULT', 'api_base_url') + 'system/directadmin/dns_write_post',
           json=dict(os.environ),
           timeout=config.getint('DEFAULT', 'api_timeout'))

    if r.status_code != 200:
        print(r.json().get('message'))
        exit(1)
