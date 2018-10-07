from six.moves import configparser

config = configparser.ConfigParser({
    'api_base_url': 'https://example.com/api/',
    'api_key': 'abcdef',
    'api_timeout': '5',
    'backups_container': 'da-backups',
})
config.read('/etc/dasa.ini')
