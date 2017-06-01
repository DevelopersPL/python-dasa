import math
import os
import logging
import time
import json
from dasa import ciapi
from dasa import osapi
from dasa.config import config
from dasa.utils import LengthWrapper

segment_limit = 5 * 1024 * 1024 * 1024


def main():
    log = logging.getLogger()
    log.info('DASA: Running user_backup_post', extra=os.environ)

    if 'username' not in os.environ or 'file' not in os.environ:
        print('Required environment variables missing, expecting: username, file')
        exit(1)

    backup_info = os.stat(os.environ.get('file'))
    time_string = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(backup_info.st_mtime))
    file_name = os.path.basename(os.environ.get('file'))
    user_name = os.environ.get('username')

    # Process to uploading the backup file
    osconn = osapi.os_connect()
    obj = None

    # max object size is 5368709122 (5 GB + 2 bytes)
    if backup_info.st_size <= segment_limit:
        with open(os.environ.get('file'), 'rb') as f:
            obj = osconn.object_store.upload_object(container=config.get('DEFAULT', 'container-backups'),
                                                    name=user_name + '/' + time_string + '/' + file_name,
                                                    data=f,
                                                    content_type='application/x-gzip')

        osconn.object_store.set_object_metadata(obj,
                                                container=config.get('DEFAULT', 'container-backups'),
                                                username=user_name,
                                                backup_time=time_string)

    else:
        # We have to send multiple segments and create a Static Large Object manifest
        segments = int(math.ceil(backup_info.st_size / segment_limit))
        uploaded_objs = []

        for segment in range(segments):
            log.info('Uploading segment %d', segment)
            f = open(os.environ.get('file'), 'rb')
            f.seek(segment * segment_limit)
            part_file = LengthWrapper(f, segment_limit, md5=False)
            obj = osconn.object_store.upload_object(
                container=config.get('DEFAULT', 'container-backups-segments'),
                name=user_name + '/' + time_string + '/' + file_name + '/' + str(segment) + '.part',
                data=part_file,
                content_type='application/x-gzip')

            uploaded_objs.append(obj)

        manifest_data = json.dumps([
            {
                'path': o.container + '/' + o.name,
                'etag': o.etag,
            } for o in uploaded_objs
        ])

        obj = osconn.object_store.upload_object(
            container=config.get('DEFAULT', 'container-backups'),
            name=user_name + '/' + time_string + '/' + file_name + '?multipart-manifest=put',
            data=manifest_data)

        osconn.object_store.set_object_metadata(obj,
                                                container=config.get('DEFAULT', 'container-backups'),
                                                username=user_name,
                                                backup_time=time_string)

        # Remove uploaded backup file now
        os.remove(os.environ.get('file'))

        # Notify CIAPI
        s = ciapi.get_session()
        s.post(config.get('DEFAULT', 'api_base_url') + 'system/directadmin/user_backup_post', json={
            'username': user_name,
            'backup_filename': file_name,
            'backup_datetime': time_string,
            'backup_size': backup_info.st_size,
            'backup_path': user_name + '/' + time_string + '/' + file_name,
        }, timeout=config.get('api_timeout'))

        if s.status_code != 200:
            exit(1)
