import keystoneauth1
from openstack.connection import from_config
from six.moves import configparser

config = configparser.ConfigParser({
    'api_base_url': 'https://example.com/api/',
    'api_key': 'abcdef',
    'api_timeout': '5',
    'backups_container': 'da-backups',
    'os_cloud': 'ovh',
})
config.read('/etc/dasa.ini')


def os_connect():
    c = from_config(config.get('DEFAULT', 'os_cloud'))
    a = keystoneauth1.session.TCPKeepAliveAdapter(max_retries=3, pool_connections=0)
    c.session
    c._session.session.mount('http://', a)
    return c
