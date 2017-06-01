from six.moves import configparser

config = configparser.ConfigParser({
    'container-backups': 'da-backups',
    'container-backups-segments': 'da-backups-segments',
    'api_base_url': 'https://example.com/api/',
    'api_key': 'abcdef',
    'api_timeout': 5,
})
config.read('/etc/dasa.ini')
