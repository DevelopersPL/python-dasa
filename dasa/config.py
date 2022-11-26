import keystoneauth1
from keystoneauth1.session import TCPKeepAliveAdapter
from openstack.connection import from_config
import requests
from six.moves import configparser

config = configparser.ConfigParser({
    'api_base_url': 'https://example.com/api/',
    'api_key': 'abcdef',
    'api_timeout': '5',
    'backups_container': 'da-backups',
    'backups_remove_local': True,
    'backups_upload': False,
    'os_cloud': 'ovh',
    'source_address': None,
})
config.read('/etc/dasa.ini')


# added: max_retries=5
def _construct_session(session_obj=None):
    # NOTE(morganfainberg): if the logic in this function changes be sure to
    # update the betamax fixture's '_construct_session_with_betamax" function
    # as well.
    if not session_obj:
        session_obj = requests.Session()
        # Use TCPKeepAliveAdapter to fix bug 1323862
        for scheme in list(session_obj.adapters):
            session_obj.mount(scheme, TCPKeepAliveSourceAddressAdapter(max_retries=5,
                                                                       source_address=config.get('DEFAULT',
                                                                                                 'source_address')))
    return session_obj


def os_connect():
    # monkey-patch to customize retrying
    keystoneauth1.session._construct_session = _construct_session
    c = from_config(config.get('DEFAULT', 'os_cloud'))
    return c


class TCPKeepAliveSourceAddressAdapter(TCPKeepAliveAdapter):
    source_address = None

    def __init__(self, **kwargs):
        if 'source_address' in kwargs:
            self.source_address = kwargs['source_address']
            del kwargs['source_address']

        super(TCPKeepAliveSourceAddressAdapter, self).__init__(**kwargs)

    def init_poolmanager(self, *args, **kwargs):
        super(TCPKeepAliveSourceAddressAdapter, self) \
            .init_poolmanager(*args,
                              source_address=(self.source_address, 0) if self.source_address else None,
                              **kwargs)
