import os


def fail_for_regular_user(message):
    # https: // www.directadmin.com / features.php?id = 1466
    if 'login_as_master_name' not in os.environ:
        print('Modyfikowanie tych opcji SpamAssassin jest zablokowane.')
        print(message)
        exit(1)


def main():
    fail_for_regular_user('Nie można wyłączyć SpamAssassina.')