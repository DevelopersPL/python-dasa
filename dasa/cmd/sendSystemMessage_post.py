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

    if 'non-existant E-Mails have just been sent by' in os.environ['subject']:
        # notify CIAPI of email abuse
        pass

    if os.environ['include_admins'] == '1':
        pass
