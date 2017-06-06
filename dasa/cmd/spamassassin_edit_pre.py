import os
from dasa import utils


def fail_for_regular_use(message):
    # https: // www.directadmin.com / features.php?id = 1466
    if 'login_as_master_name' not in os.environ:
        print('Modyfikowanie tych opcji SpamAssassin jest zablokowane.')
        print(message)
        exit(1)


# https://www.directadmin.com/features.php?id=1702
def main():
    utils.log_with_env('spamassassin_edit_pre', env=dict(os.environ))

    if 'where' in os.environ and os.environ.get('where') == 'inbox' or os.environ.get('where') == 'spamfolder':
        fail_for_regular_use('Spam możesz przekazywać do katalogu spam lub usuwać.')

    if 'high_score_block' in os.environ and os.environ.get('high_score_block') == 'no':
        fail_for_regular_use('Usuwanie wysoko punktowanego spamu musi być włączone.')

    if 'high_score' in os.environ:
        hs = int(os.environ.get('high_score'))
        if hs == 0 or hs > 15:
            fail_for_regular_use('Maksymalna wartość wysoko punktowanego spamu to 15.')

    if 'required_hits' in os.environ:
        if os.environ.get('required_hits') == 'custom':
            rh = float(os.environ.get('required_hits_custom'))
        else:
            rh = float(os.environ.get('required_hits'))

        if rh > 5.0:
            fail_for_regular_use('Maksymalna wartość spamu to 5.0.')
