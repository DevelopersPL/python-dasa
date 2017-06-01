import os
from dasa import ciapi
from dasa.config import config


def main():
    s = ciapi.get_session()

    # domain_create_post for newdomain
    json = os.environ
    old_domain = json.domain
    json.domain = json.newdomain
    del json.newdomain
    s.post(config.get('DEFAULT', 'api_base_url') + 'system/directadmin/domain_create_post',
           json=json,
           timeout=config.getint('DEFAULT', 'api_timeout'))

    if s.status_code == 404:
        print(s.json().get('message'))
        exit(0)

    if s.status_code != 200:
        print(s.json().get('message'))
        exit(1)

    # domain_destroy_post for (old) domain
    json.domain = old_domain
    s.post(config.get('DEFAULT', 'api_base_url') + 'system/directadmin/domain_destroy_post',
           json=json,
           timeout=config.getint('DEFAULT', 'api_timeout'))

    if s.status_code == 404:
        print(s.json().get('message'))
        exit(0)

    if s.status_code != 200:
        print(s.json().get('message'))
        exit(1)
