import logging
import subprocess

from dasa import utils

# lvectl option per CIAPI field
LVE_LIMITS = (
    ('limit_lve_cpu', '--speed=%s%%'),
    ('limit_lve_pmem', '--pmem=%sM'),
    ('limit_lve_io', '--io=%s'),
    ('limit_lve_iops', '--iops=%s'),
    ('limit_lve_ep', '--maxEntryProcs=%s'),
    ('limit_lve_nproc', '--nproc=%s'),
)


def apply_state(daa):
    """Apply the account state reported by CIAPI: mail blacklists, LVE limits, PHP version.

    Shared by user_create_post and user_modify_post so an account keeps the same
    state after every DirectAdmin change, not only at creation. Fields are read
    with .get() - a CIAPI old enough to omit one must not abort the whole hook.
    """
    username = daa['username']

    # Apply block_emails_scripts
    # https://help.directadmin.com/item.php?id=655
    utils.file_ensure_da_user('/etc/virtual/blacklist_script_usernames', username,
                              daa.get('block_emails_scripts', False))

    # Apply block_emails_all
    utils.file_ensure_da_user('/etc/virtual/blacklist_usernames', username,
                              daa.get('block_emails_all', False))

    apply_lve_limits(daa, username)

    # Set PHP version
    if daa.get('php_version'):
        run(['/usr/bin/selectorctl', '-u', username, '-b', str(daa['php_version'])])


def apply_lve_limits(daa, username):
    run(['/usr/sbin/lvectl', 'set-user', username, '--default=all'])

    lve_line = ['/usr/sbin/lvectl', 'set-user', username]
    for field, option in LVE_LIMITS:
        if daa.get(field):
            lve_line.append(option % daa[field])

    if len(lve_line) > 3:
        run(lve_line)


def run(command):
    try:
        subprocess.check_call(command)
    except (subprocess.CalledProcessError, OSError) as e:
        utils.plog(logging.ERROR, e, exc_info=True)
        logging.error('Wystąpił błąd: %s' % e)
