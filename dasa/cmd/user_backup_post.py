import openstack

import logging
import os
import time

from dasa import ciapi
from dasa.config import config
from dasa.config import os_connect
from dasa import utils

# max object size is 5368709122 (5 GB + 2 bytes)
segment_limit = 5 * 1024 * 1024 * 1024


def main():
    utils.log_with_env('user_backup_post', env=dict(os.environ))

    if 'username' not in os.environ or 'file' not in os.environ:
        logging.error('Required environment variables missing, expecting: username, file')
        exit(1)

    backup_info = os.stat(os.environ.get('file'))
    time_string = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(backup_info.st_mtime))
    file_name = os.path.basename(os.environ.get('file'))
    user_name = os.environ.get('username')

    # monkey patch this crap
    def _upload_object(self, endpoint, filename, headers):
        return openstack._adapter._json_response(self.object_store.put(
            endpoint, headers=headers, data=open(filename, 'rb')))  # add 'b'
    openstack.cloud.openstackcloud._OpenStackCloudMixin._upload_object = _upload_object

    try:
        c = os_connect()
        start_time = time.clock()
        c.create_object(container=config.get('DEFAULT', 'backups_container'),
                        name=user_name + '/' + time_string + '/' + file_name,
                        filename=os.environ.get('file'),
                        segment_size=segment_limit,  # optional, should auto-discover
                        metadata={
                            'username': user_name,
                            'backup_time': time_string
                        },
                        **{'content-type': 'application/x-gzip'})

        # Print timing
        elapsed = time.clock() - start_time
        size = utils.sizeof_fmt(backup_info.st_size / elapsed)
        logging.info('Upload of %s finished in %d seconds (%s/s)' % (file_name, elapsed, size))

        # Remove local backup file now
        os.remove(os.environ.get('file'))

        # Report to CIAPI
        s = ciapi.get_session()
        r = s.post('system/directadmin/user_backup_post', json={
            'username': user_name,
            'backup_filename': file_name,
            'backup_datetime': time_string,
            'backup_size': backup_info.st_size,
            'backup_path': user_name + '/' + time_string + '/' + file_name,
            'container': config.get('DEFAULT', 'backups_container'),
        }, )

        if r.status_code != 200:
            logging.error(r.json().get('message', None))
            exit(1)
    except Exception as e:
        utils.plog(logging.ERROR, e, exc_info=True)
        logging.error('Wystąpił błąd: %s' % e)
        exit(2)
