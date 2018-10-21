import sys
import logging

from systemd import journal

root = logging.getLogger()
root.setLevel(logging.DEBUG)

root = logging.getLogger()
root.setLevel(logging.DEBUG)

# logging to journal
root.addHandler(journal.JournalHandler(logging.DEBUG, SYSLOG_IDENTIFIER='dasa'))

# logging to user/browser/DA
out_handler = logging.StreamHandler(sys.stderr)
out_handler.setLevel(logging.INFO)
out_handler.setFormatter(logging.Formatter('%(message)s'))
root.addHandler(out_handler)

# private logging
plogger = logging.getLogger('dasa.private')
plogger.setLevel(logging.DEBUG)
plogger.addHandler(journal.JournalHandler(logging.DEBUG, SYSLOG_IDENTIFIER='dasa'))
plogger.propagate = False

# configure logging for requests
rlogger = logging.getLogger('requests.packages.urllib3')
rlogger.setLevel(logging.INFO)
rlogger.addHandler(journal.JournalHandler(logging.DEBUG, SYSLOG_IDENTIFIER='dasa'))
rlogger.propagate = False
