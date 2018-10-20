import requests

import logging
import os

from dasa import ciapi
from dasa.config import config
from dasa import utils


def main():
    utils.log_with_env('sendSystemMessage_pre', env=dict(os.environ))
    if 'subject' not in os.environ:
        logging.error('Required environment variables missing, expecting: subject, message, ...')
        exit(1)
