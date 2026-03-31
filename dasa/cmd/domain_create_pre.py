import requests

import logging
import os

from dasa import ciapi
from dasa import utils


# https://www.directadmin.com/features.php?id=1983
def main():
    utils.log_with_env('domain_create_pre', env=dict(os.environ))

    try:
        # Report to CIAPI
        s = ciapi.get_session()
        r = s.post('system/directadmin/domain_create_pre', json=dict(os.environ))

        if r.status_code == 404:
            logging.info(ciapi.get_message(r))
            exit(0)

        if r.status_code != 200:
            logging.info(ciapi.get_message(r))
            exit(1)
    except (requests.exceptions.RequestException, ValueError) as e:
        utils.plog(logging.ERROR, e, exc_info=True)
        logging.warning('API niedostępne, kontynuowanie tworzenia domeny: %s' % e)
        exit(0)
