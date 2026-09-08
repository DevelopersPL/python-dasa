import requests

import logging
import os
import pwd
import grp

from dasa import account
from dasa import ciapi
from dasa import utils


def main():
    utils.log_with_env('user_create_post', env=dict(os.environ))

    try:
        # Report to CIAPI
        s = ciapi.get_session()
        r = s.post('system/directadmin/user_create_post', json=dict(os.environ))

        if r.status_code == 404:
            logging.error(ciapi.get_message(r))
            exit(0)

        if r.status_code != 200:
            logging.error(ciapi.get_message(r))
            exit(1)
    except (requests.exceptions.RequestException, ValueError) as e:
        utils.plog(logging.ERROR, e, exc_info=True)
        logging.error('Wystąpił błąd: %s' % e)
        exit(2)

    try:
        daa = r.json()
    except ValueError as e:
        logging.error('Invalid JSON response from CIAPI: %s' % e)
        exit(1)

    # Ensure SpamAssassin settings exist
    if 'user_creation' in os.environ and os.environ['user_creation'] == '1':
        if not os.path.isdir('/home/' + daa['username'] + '/.spamassassin'):
            os.mkdir('/home/' + daa['username'] + '/.spamassassin', 0o771)
            uid = pwd.getpwnam(daa['username']).pw_uid
            gid = grp.getgrnam('mail').gr_gid
            os.chown('/home/' + daa['username'] + '/.spamassassin', uid, gid)  # $username:mail

            if not os.path.isfile('/home/' + daa['username'] + '/.spamassassin/user_prefs'):
                with open('/home/' + daa['username'] + '/.spamassassin/user_prefs', 'w') as f:
                    f.write("required_score 5.0\nreport_safe 1\n")
                os.chmod('/home/' + daa['username'] + '/.spamassassin/user_prefs', 0o755)
                gid = grp.getgrnam(daa['username']).gr_gid
                os.chown('/home/' + daa['username'] + '/.spamassassin/user_prefs', uid, gid)  # $username:$username

            if not os.path.isfile('/home/' + daa['username'] + '/.spamassassin/spam'):
                with open('/home/' + daa['username'] + '/.spamassassin/spam', 'w'):
                    pass
                os.chmod('/home/' + daa['username'] + '/.spamassassin/spam', 0o660)
                uid = pwd.getpwnam('mail').pw_uid
                os.chown('/home/' + daa['username'] + '/.spamassassin/spam', uid, gid)  # mail:$username

    account.apply_state(daa)
