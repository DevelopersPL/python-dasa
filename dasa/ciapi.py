import requests
from dasa.config import config


def get_session():
    s = requests.Session()
    s.headers.update({'X-DASA-Key': config.get('api_key')})
    return s
