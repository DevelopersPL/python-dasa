import requests

import logging
import os

from dasa import ciapi
from dasa import utils


# https://www.directadmin.com/features.php?id=2215
def main():
    utils.log_with_env('sendSystemMessage_post', env=dict(os.environ))
    if 'subject' not in os.environ:
        logging.error('Required environment variables missing, expecting: subject')
        exit(1)

    if 'emails have just been sent by' in os.environ['subject']:
        # notify CIAPI of email abuse
        pass

    if 'non-existent E-Mails have just been sent by' in os.environ['subject']:
        # notify CIAPI of email abuse
        pass

    if os.environ['include_admins'] == '1':
        return  # duplicate

    try:
        # Report to CIAPI
        s = ciapi.get_session()
        r = s.post('system/directadmin/send_system_message_post', json=dict(os.environ))

        if r.status_code == 404:
            logging.info(r.json().get('message'))
            exit(0)

        if r.status_code != 200:
            logging.info(r.json().get('message'))
            exit(1)
    except requests.exceptions.RequestException as e:
        utils.plog(logging.ERROR, e, exc_info=True)
        logging.error('Wystąpił błąd: %s' % e)
        exit(2)
