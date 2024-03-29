import requests

import logging
import os
import pwd
import grp
import subprocess

from dasa import ciapi
from dasa import utils


def main():
    utils.log_with_env('user_create_post', env=dict(os.environ))

    try:
        # Report to CIAPI
        s = ciapi.get_session()
        r = s.post('system/directadmin/user_create_post', json=dict(os.environ))

        if r.status_code == 404:
            logging.error(r.json().get('message'))
            exit(0)

        if r.status_code != 200:
            logging.error(r.json().get('message'))
            exit(1)
    except requests.exceptions.RequestException as e:
        utils.plog(logging.ERROR, e, exc_info=True)
        logging.error('Wystąpił błąd: %s' % e)
        exit(2)

    daa = r.json()

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

    # Apply block_emails_scripts
    # https://help.directadmin.com/item.php?id=655
    utils.file_ensure_da_user('/etc/virtual/blacklist_script_usernames', daa['username'], daa['block_emails_scripts'])

    # Apply block_emails_all
    utils.file_ensure_da_user('/etc/virtual/blacklist_usernames', daa['username'], daa['block_emails_all'])

    # Apply LVE limits
    try:
        subprocess.check_call(['/usr/sbin/lvectl', 'set-user', daa['username'], '--default=all'])
    except subprocess.CalledProcessError as e:
        utils.plog(logging.ERROR, e, exc_info=True)
        logging.error('Wystąpił błąd: %s' % e)

    lve_line = ['/usr/sbin/lvectl', 'set-user', daa['username']]
    if daa['limit_lve_cpu']:
        lve_line.append('--speed=' + str(daa['limit_lve_cpu']) + '%')
    if daa['limit_lve_pmem']:
        lve_line.append('--pmem=' + str(daa['limit_lve_pmem']) + 'M')
    if daa['limit_lve_io']:
        lve_line.append('--io=' + str(daa['limit_lve_io']))
    if daa['limit_lve_iops']:
        lve_line.append('--iops=' + str(daa['limit_lve_iops']))
    if daa['limit_lve_ep']:
        lve_line.append('--maxEntryProcs=' + str(daa['limit_lve_ep']))
    if daa['limit_lve_nproc']:
        lve_line.append('--nproc=' + str(daa['limit_lve_nproc']))
    if daa['limit_lve_iops']:
        lve_line.append('--iops=' + str(daa['limit_lve_iops']))
    if len(lve_line) > 3:
        try:
            subprocess.check_call(lve_line)
        except subprocess.CalledProcessError as e:
            utils.plog(logging.ERROR, e, exc_info=True)
            logging.error('Wystąpił błąd: %s' % e)

    # Set PHP version
    if daa['php_version']:
        subprocess.check_call(['/usr/bin/selectorctl', '-u', daa['username'], '-b', daa['php_version']])
