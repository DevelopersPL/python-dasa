import os
from dasa import ciapi
from dasa.config import config


def main():
    s = ciapi.get_session()
    s.post(config.get('DEFAULT', 'api_base_url') + 'system/directadmin/domain_pointer_create_post',
           json=os.environ,
           timeout=config.get('DEFAULT', 'api_timeout'))

    if s.status_code == 404:
        print(s.json().get('message'))
        exit(0)

    if s.status_code != 200:
        print(s.json().get('message'))
        exit(1)
