import requests
from requests import HTTPAdapter
# Python 2 compatibility
from requests.packages.urllib3.util.retry import Retry

from dasa.config import config


def get_session():
    s = SessionWithUrlBase(url_base=config.get('DEFAULT', 'api_base_url'))
    s.headers.update({
        'X-DASA-Key': config.get('DEFAULT', 'api_key'),
        'Accept': 'application/json',
    })
    return s


# https://stackoverflow.com/a/43882437
class SessionWithUrlBase(requests.Session):
    # In Python 3 you could place `url_base` after `*args`, but not in Python 2.
    def __init__(self, url_base=None, *args, **kwargs):
        super(SessionWithUrlBase, self).__init__(*args, **kwargs)
        self.url_base = url_base
        self.retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])

    def request(self, method, url, **kwargs):
        # Next line of code is here for example purposes only.
        # You really shouldn't just use string concatenation here,
        # take a look at urllib.parse.urljoin instead.
        modified_url = self.url_base + url

        # set default timeout if none provided
        if 'timeout' not in kwargs:
            kwargs['timeout'] = config.getint('DEFAULT', 'api_timeout')

        adapter = HTTPAdapter(max_retries=self.retries)
        self.mount('http://', adapter)
        self.mount('https://', adapter)
        
        return super(SessionWithUrlBase, self).request(method, modified_url, **kwargs)
