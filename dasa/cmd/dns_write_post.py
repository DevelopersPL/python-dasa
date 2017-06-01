import os
from dasa import ciapi
from dasa.config import config


def main():
    s = ciapi.get_session()
    s.post(config.get('DEFAULT', 'api_base_url') + 'system/directadmin/dns_write_post',
           json=dict(os.environ),
           timeout=config.getint('DEFAULT', 'api_timeout'))

    if s.status_code != 200:
        print(s.json().get('message'))
        exit(1)
