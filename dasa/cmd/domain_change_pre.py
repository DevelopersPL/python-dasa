import requests

import logging
import os

from dasa import ciapi
from dasa.config import config
from dasa import utils


def main():
    utils.log_with_env('domain_change_pre', env=dict(os.environ))

    try:
        # Report to CIAPI
        s = ciapi.get_session()

        # pre-clear via domain_create_pre
        json = dict(os.environ)
        json['domain'] = json['newdomain']
        del json['newdomain']
        r = s.post(config.get('DEFAULT', 'api_base_url') + 'system/directadmin/domain_create_pre',
                   json=json,
                   timeout=config.getint('DEFAULT', 'api_timeout'))

        if r.status_code == 404:
            logging.info(r.json().get('message'))
            exit(0)

        if r.status_code != 200:
            logging.info(r.json().get('message'))
            exit(1)
    except requests.exceptions.RequestException as e:
        utils.plog(logging.ERROR, e, exc_info=True)
        logging.error(e)
        exit(2)
