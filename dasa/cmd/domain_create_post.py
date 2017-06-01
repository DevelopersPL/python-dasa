import os
from dasa import ciapi
from dasa.config import config


def main():
    if 'username' not in os.environ or 'domain' not in os.environ:
        print('Required environment variables missing, expecting: username, domain')
        exit(1)

    # Set SpamAssassin options
    if os.path.isfile('/etc/virtual/' + os.environ.get('domain') + '/filter.conf'):
        with open('/etc/virtual/' + os.environ.get('domain') + '/filter.conf', 'a') as f:
            f.write("high_score=15\nhigh_score_block=yes\nwhere=userspamfolder\n")

        with open('/usr/local/directadmin/data/task.queue', 'a') as f:
            f.write('action=rewrite&value=filter&user=' + os.environ.get('username'))

    # Report to CIAPI
    s = ciapi.get_session()
    s.post(config.get('DEFAULT', 'api_base_url') + 'system/directadmin/domain_create_post',
           json=dict(os.environ),
           timeout=config.getint('DEFAULT', 'api_timeout'))

    if s.status_code == 404:
        print(s.json().get('message'))
        exit(0)

    if s.status_code != 200:
        print(s.json().get('message'))
        exit(1)
