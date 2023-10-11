import json
import logging
import os
import subprocess
import requests

from dasa import ciapi
from dasa.config import config
from dasa import utils


def main():
    utils.log_with_env('user_backup_compress_pre', env=dict(os.environ))

    if 'username' not in os.environ:
        logging.error('Required environment variables missing, expecting: username')
        exit(1)

    if not config.getboolean('DEFAULT', 'borg_enabled'):
        exit(0)

    username = os.environ.get('username')
    prefix = config.get('DEFAULT', 'borg_repo_prefix')
    os.chdir(f'/home/admin/admin_backups/{username}')
    os.environ.update({
        'BORG_PASSPHRASE': config.get('DEFAULT', 'borg_passphrase'),
        'BORG_REPO': f"{prefix}{username}",
        'TZ': 'UTC',
    })

    logging.info(f'running init create for {username}...')
    # init - this usually fails on subsequent runs when repository exists
    # there's no good way to tell (same exit code)
    borg_init = subprocess.run([
        'borg', 'init', '--encryption', 'repokey', '--make-parent-dirs',
    ], universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if borg_init.returncode != 0:
        logging.error(f'borg init failed for {username}: {borg_init.stderr}')

    # CREATE
    logging.info(f'running borg create for {username}...')
    borg_create = subprocess.run([
        'borg', 'create', '--json', '--sparse', '--one-file-system', '--exclude-caches',
        '--compression', 'zstd',
        '-e', f'/home/{username}/backups',
        '-e', f'/home/{username}/.trash',
        '-e', f'/home/{username}/.cache',
        '-e', f'/home/{username}/.cagefs',
        '-e', f'/home/{username}/tmp',
        '-e', f'backup/home.tar*',
        '-e', f'domains/',  # usually not present unless DA backup didn't exclude domain data
        '-e', f'imap/',  # usually not present unless DA backup didn't exclude email data
        f'::{username}_{{now:%Y-%m-%dT%H:%M:%S}}',
        '.', f'/home/{username}',
    ], universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if borg_create.returncode != 0:
        logging.error(f'borg backup failed for {username}: {borg_create.stderr}')
        exit(1)

    try:
        # Report CREATE to CIAPI
        s = ciapi.get_session()
        r = s.post('system/directadmin/user_backup_compress_pre', json={
            'username': username,
            'borg': json.loads(borg_create.stdout),
        })

        if r.status_code != 200:
            logging.error(dict(r.json()).get('message', None))

        response = dict(r.json())
    except (requests.exceptions.RequestException, json.decoder.JSONDecodeError) as e:
        utils.plog(logging.ERROR, e, exc_info=True)
        logging.error('Wystąpił błąd: %s' % e)
        response = {}

    # PRUNE
    logging.info(f'running borg prune for {username}...')
    borg_prune = subprocess.run([
        'borg', 'prune', '-v', '--stats',
        '--glob-archives', f'{username}_*',
        f"--keep-within={response.get('keep_within', '1H')}",
        f"--keep-last={response.get('keep_last', 7)}",
        f"--keep-minutely={response.get('keep_minutely', 0)}",
        f"--keep-hourly={response.get('keep_hourly', 0)}",
        f"--keep-daily={response.get('keep_daily', 7)}",
        f"--keep-weekly={response.get('keep_weekly', 4)}",
        f"--keep-monthly={response.get('keep_monthly', 3)}",
        f"--keep-yearly={response.get('keep_yearly', 0)}",
    ], universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    if borg_prune.returncode > 0:
        logging.error(f'borg prune failed for {username}: {borg_prune.stdout}')
    else:
        logging.info(f'borg prune completed for {username}: {borg_prune.stdout}')

    # COMPACT
    logging.info(f'running borg compact for {username}...')
    borg_compact = subprocess.run([
        'borg', 'compact',
    ], universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    if borg_compact.returncode > 0:
        logging.error(f'borg prune failed for {username}: {borg_compact.stdout}')
    else:
        logging.info(f'borg prune completed for {username}: {borg_compact.stdout}')

    # Report ARCHIVE LIST to CIAPI
    logging.info(f'running borg list for {username}...')
    borg_list = subprocess.run([
        'borg', 'list', '--short',
    ], universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if borg_compact.returncode > 0:
        logging.error(f'borg list failed for {username}: {borg_list.stderr}')

    archives = []
    for archive in borg_list.stdout.splitlines():
        logging.info(f'running borg info for {username}::{archive}...')
        borg_info = subprocess.run([
            'borg', 'info', '--json', f"{prefix}{username}::{archive}",
        ], universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if borg_info.returncode == 0:
            archives.append(json.loads(borg_info.stdout))
        else:
            logging.error(f'borg list failed for {username}::{archive}: {borg_info.stderr}')

    try:
        r = s.post('system/directadmin/borg-archives', json={
            'username': username,
            'borg-archives': archives,
        })
        if r.status_code != 200:
            logging.error(dict(r.json()).get('message', None))
    except (requests.exceptions.RequestException, json.decoder.JSONDecodeError) as e:
        utils.plog(logging.ERROR, e, exc_info=True)
        logging.error('Wystąpił błąd: %s' % e)
