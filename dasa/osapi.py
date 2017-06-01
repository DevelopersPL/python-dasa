from openstack.connection import from_config


def os_connect():
    return from_config('ovh')
