import os
from dasa import utils


def fail_for_regular_user(message):
    # https://www.directadmin.com/features.php?id=1466
    if 'login_as_master_name' not in os.environ:
        print('Modyfikowanie tych opcji SpamAssassin jest zablokowane.')
        print(message)
        exit(1)


def main():
    utils.log_with_env('spamassassin_destroy_pre', env=dict(os.environ))

    fail_for_regular_user('Nie można wyłączyć SpamAssassina.')
