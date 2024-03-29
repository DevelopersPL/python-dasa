import hashlib
import fileinput
import logging
import os
import re
import time


def plog(lvl, msg, *args, **kwargs):
    plogger = logging.getLogger('dasa.private')
    return plogger.log(lvl, msg, *args, **kwargs)


def log_with_env(message='dasa log env', env=None):
    logging.log(logging.DEBUG, message, extra=env_to_log_extra_def(env))


def env_to_log_extra_def(env=None):
    if env is None:
        env = dict(os.environ)

    journal_extra = {}
    for k, v in env.items():
        # JournalD accepts only uppercase alphanumeric keys
        k = re.sub(r'[^A-Z0-9]+', '_', k.upper())
        journal_extra['DA_HOOK_ENV_' + k] = v
    return journal_extra


def file_ensure_da_user(path, username, exists=True):
    if exists:
        with open(path, 'a+') as f:
            if not any(username == x.split(':', maxsplit=1)[0].strip() for x in f):
                f.write(username + ':' + str(int(time.time())) + '\n')
    else:
        try:
            for l in fileinput.input(path, inplace=True):
                if l.split(':', maxsplit=1)[0].strip() != username:
                    print(l.strip())
        except OSError:
            # Ignore if file does not exist
            pass


def sizeof_fmt(num, suffix='B'):
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


class NoopMD5(object):
    def __init__(self, *a, **kw):
        pass

    def update(self, *a, **kw):
        pass

    def hexdigest(self, *a, **kw):
        return ''


# https://github.com/openstack/python-swiftclient/blob/master/swiftclient/utils.py#L297
class LengthWrapper(object):
    """
    Wrap a filelike object with a maximum length.
    Fix for https://github.com/kennethreitz/requests/issues/1648.
    It is recommended to use this class only on files opened in binary mode.
    """

    def __init__(self, readable, length, md5=False):
        """
        :param readable: The filelike object to read from.
        :param length: The maximum amount of content that can be read from
                       the filelike object before it is simulated to be
                       empty.
        :param md5: Flag to enable calculating the MD5 of the content
                    as it is read.
        """
        self._md5 = md5
        self._reset_md5()
        self._length = self._remaining = length
        self._readable = readable
        self._can_reset = all(hasattr(readable, attr)
                              for attr in ('seek', 'tell'))
        if self._can_reset:
            self._start = readable.tell()

    def __len__(self):
        return self._length

    def _reset_md5(self):
        self.md5sum = hashlib.md5() if self._md5 else NoopMD5()

    def get_md5sum(self):
        return self.md5sum.hexdigest()

    def read(self, size=-1):
        if self._remaining <= 0:
            return ''

        to_read = self._remaining if size < 0 else min(size, self._remaining)
        chunk = self._readable.read(to_read)
        self._remaining -= len(chunk)

        try:
            self.md5sum.update(chunk)
        except TypeError:
            self.md5sum.update(chunk.encode())

        return chunk

    @property
    def reset(self):
        if self._can_reset:
            return self._reset
        raise AttributeError("%r object has no attribute 'reset'" %
                             type(self).__name__)

    def _reset(self, *args, **kwargs):
        if not self._can_reset:
            raise TypeError('%r object cannot be reset; needs both seek and '
                            'tell methods' % type(self._readable).__name__)
        self._readable.seek(self._start)
        self._reset_md5()
        self._remaining = self._length
