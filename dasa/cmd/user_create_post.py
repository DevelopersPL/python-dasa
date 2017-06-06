import os
import errno
import pwd
import grp
import subprocess

from dasa import ciapi
from dasa.config import config
import dasa.utils as utils


def main():
    utils.log_with_env('user_create_post', dict(os.environ))

    s = ciapi.get_session()
    r = s.post(config.get('DEFAULT', 'api_base_url') + 'system/directadmin/user_create_post',
               json=dict(os.environ),
               timeout=config.getint('DEFAULT', 'api_timeout'))

    if r.status_code == 404:
        print(r.json().get('message'))
        exit(0)

    if r.status_code != 200:
        print(r.json().get('message'))
        exit(1)

    daa = r.json()

    # Ensure SpamAssassin settings exist
    if not os.path.isdir('/home/' + daa['username'] + '/.spamassassin'):
        os.mkdir('/home/' + daa['username'] + '/.spamassassin', 0x771)
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
    utils.file_ensure_line('/etc/virtual/blacklist_script_usernames', daa['username'], daa['block_emails_scripts'])

    # Apply block_emails_all
    utils.file_ensure_line('/etc/virtual/blacklist_usernames', daa['username'], daa['block_emails_all'])

    # Apply limit_emails
    if daa['limit_emails'] or os.environ.get('email_limit'):
        with open('/etc/virtual/limit_' + daa['username'], 'w') as f:
            if daa['limit_emails']:
                f.write(str(daa['limit_emails']) + "\n")
            else:
                f.write(os.environ.get('email_limit') + "\n")
        os.chmod('/etc/virtual/limit_' + daa['username'], 0o755)  # DA uses that chmod
        uid = pwd.getpwnam('mail').pw_uid
        gid = grp.getgrnam('mail').gr_gid
        os.chown('/etc/virtual/limit_' + daa['username'], uid, gid)  # mail:mail
    else:
        try:
            os.remove('/etc/virtual/limit_' + daa['username'])
        except OSError as e:
            if e.errno != errno.ENOENT:  # errno.ENOENT = no such file or directory
                raise

    # Apply LVE limits
    subprocess.check_call(['/usr/sbin/lvectl', 'set-user', daa['username'], '--default=all'])
    lve_line = ['/usr/sbin/lvectl', 'set-user', daa['username']]
    if daa['limit_lve_cpu']:
        lve_line.append('--speed=' + str(daa['limit_lve_cpu']) + '%')
    if daa['limit_lve_pmem']:
        lve_line.append('--pmem=' + str(daa['limit_lve_pmem']))
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
        subprocess.check_call(lve_line)

    # Set PHP version
    if daa['php_version']:
        subprocess.check_call(['/usr/bin/selectorctl', '-u', daa['username'], '-b', daa['php_version']])

    # Run CloudLinux hooks
    subprocess.check_call('/usr/share/cagefs-plugins/hooks/directadmin/user_create_post.sh')
    subprocess.check_call(['/usr/bin/da-addsudoer', daa['username'], 'add_cagefs_user'])
    subprocess.call(['/usr/bin/da_add_admin', daa['username']])  # ignore exit code because it's 1 for non-admins
