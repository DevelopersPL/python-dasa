import requests

import logging
import os

from dasa import ciapi
from dasa import utils


def main():
    utils.log_with_env('user_backup_pre', env=dict(os.environ))

    try:
        # Report to CIAPI
        s = ciapi.get_session()
        r = s.post('system/directadmin/user_backup_pre', json=dict(os.environ))

        if r.status_code == 404:
            logging.info(r.json().get('message'))
            exit(0)

        if r.status_code != 200:
            logging.info(r.json().get('message'))
            exit(1)
    except requests.exceptions.RequestException as e:
        utils.plog(logging.ERROR, e, exc_info=True)
        logging.error('Wystąpił błąd: %s' % e)
        exit(0)  # NON FATAL - DON'T BLOCK THE BACKUP
