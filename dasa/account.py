import errno
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

# Keys CIAPI has to send before the agent touches account state. Reading them with
# a default would turn a trimmed response into "no blocks, no limits" and quietly
# unblock an abusing account or drop its limits, so a partial payload changes
# nothing instead.
REQUIRED_FIELDS = (
    'username',
    'block_emails_scripts',
    'block_emails_all',
    'limit_lve_cpu',
    'limit_lve_pmem',
    'limit_lve_io',
    'limit_lve_iops',
    'limit_lve_ep',
    'limit_lve_nproc',
    'php_version',
)


class IncompleteState(Exception):
    """CIAPI answered without the full account state, so nothing was applied."""


def apply_state(daa):
    """Apply the account state reported by CIAPI: mail blacklists, LVE limits, PHP version.

    Shared by user_create_post and user_modify_post so an account keeps the same
    state after every DirectAdmin change, not only at creation.

    Raises IncompleteState before any mutation when the payload is not complete.
    Returns False when a command ran and failed, so the hook can exit non-zero
    instead of reporting success over a stale limit.
    """
    missing = [field for field in REQUIRED_FIELDS if field not in daa]
    if missing:
        raise IncompleteState('CIAPI response is missing: %s' % ', '.join(missing))

    username = daa['username']

    # Apply block_emails_scripts
    # https://help.directadmin.com/item.php?id=655
    utils.file_ensure_da_user('/etc/virtual/blacklist_script_usernames', username,
                              daa['block_emails_scripts'])

    # Apply block_emails_all
    utils.file_ensure_da_user('/etc/virtual/blacklist_usernames', username,
                              daa['block_emails_all'])

    applied = apply_lve_limits(daa, username)

    # Set PHP version
    if daa['php_version']:
        applied = run(['/usr/bin/selectorctl', '-u', username, '-b', str(daa['php_version'])]) and applied

    return applied


def apply_lve_limits(daa, username):
    # CIAPI is the only source of truth for these limits, so the account is reset to
    # the package defaults first and the stored overrides are re-applied on top.
    applied = run(['/usr/sbin/lvectl', 'set-user', username, '--default=all'])

    lve_line = ['/usr/sbin/lvectl', 'set-user', username]
    for field, option in LVE_LIMITS:
        if daa[field]:
            lve_line.append(option % daa[field])

    if len(lve_line) > 3:
        applied = run(lve_line) and applied

    return applied


def run(command):
    """Run a state command. False means it ran and failed; a box without the binary
    (no CloudLinux) is reported as a warning, not as a failed hook."""
    try:
        subprocess.check_call(command)
    except OSError as e:
        if e.errno == errno.ENOENT:
            logging.warning('Polecenie niedostępne: %s' % command[0])
            return True

        utils.plog(logging.ERROR, e, exc_info=True)
        logging.error('Wystąpił błąd: %s' % e)
        return False
    except subprocess.CalledProcessError as e:
        utils.plog(logging.ERROR, e, exc_info=True)
        logging.error('Wystąpił błąd: %s' % e)
        return False

    return True
