from six.moves.urllib import parse

import logging
import os

from dasa import utils


# https://www.directadmin.com/features.php?id=2215
def main():
    utils.log_with_env('sendSystemMessage_pre', env=dict(os.environ))
    if 'subject' not in os.environ:
        logging.error('Required environment variables missing, expecting: subject, message, ...')
        exit(1)

    users = parse.parse_qs(os.environ['users'])

    if os.environ['subject'] == 'License File has been updated':
        # Suppress this useless message
        exit(1)
