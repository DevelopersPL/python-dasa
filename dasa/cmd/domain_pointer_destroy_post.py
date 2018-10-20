import requests

import logging
import os

from dasa import ciapi
from dasa import utils


def main():
    utils.log_with_env('domain_pointer_destroy_post', env=dict(os.environ))

    try:
        # Report to CIAPI
        s = ciapi.get_session()
        r = s.post('system/directadmin/domain_pointer_destroy_post', json=dict(os.environ))

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
