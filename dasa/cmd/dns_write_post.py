import requests

import logging
import os

from dasa import ciapi
from dasa.config import config
from dasa import utils


def main():
    utils.log_with_env('dns_write_post', env=dict(os.environ))
    if 'DOMAIN' not in os.environ:
        logging.error('Required environment variables missing, expecting: DOMAIN')
        exit(1)

    try:
        # Report to CIAPI
        s = ciapi.get_session()
        r = s.post(config.get('DEFAULT', 'api_base_url') + 'system/directadmin/dns_write_post',
                   json=dict(os.environ),
                   timeout=config.getint('DEFAULT', 'api_timeout'))

        if r.status_code != 200:
            logging.info(r.json().get('message'))
            exit(1)
    except requests.exceptions.RequestException as e:
        utils.plog(logging.ERROR, e, exc_info=True)
        logging.error(e)
        exit(2)
