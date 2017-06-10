import math
import os
import logging
import time
import json
import psutil

from openstack.exceptions import HttpException
from retry import retry
from retry.api import retry_call

from dasa import ciapi
from dasa import osapi
from dasa.config import config
from dasa.utils import LengthWrapper
from dasa import utils

segment_limit = 1 * 1024 * 1024 * 1024


def main():
    utils.log_with_env('user_backup_post', env=dict(os.environ))

    if 'username' not in os.environ or 'file' not in os.environ:
        print('Required environment variables missing, expecting: username, file')
        exit(1)

    p = psutil.Process(os.getpid())
    p.nice(0)

    backup_info = os.stat(os.environ.get('file'))
    time_string = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(backup_info.st_mtime))
    file_name = os.path.basename(os.environ.get('file'))
    user_name = os.environ.get('username')

    # max object size is 5368709122 (5 GB + 2 bytes)
    if backup_info.st_size <= segment_limit:
        obj = upload_file(os.environ.get('file'), user_name + '/' + time_string + '/' + file_name)

        try:
            osconn = osapi.os_connect()
            osconn.object_store.set_object_metadata(obj,
                                                    container=config.get('DEFAULT', 'container-backups'),
                                                    username=user_name,
                                                    backup_time=time_string)
        except HttpException:
            # We don't really need metadata that much, it's not worth aborting the whole backup
            pass

    else:
        # We have to send multiple segments and create a Static Large Object manifest
        segments = int(math.ceil(backup_info.st_size / segment_limit))
        uploaded_objs = []

        try:
            for segment in range(segments):
                logging.info('Uploading segment %d', segment)
                obj = upload_file(os.environ.get('file'),
                                  user_name + '/' + time_string + '/' + file_name + '/' + str(segment) + '.part',
                                  segment * segment_limit, segment_limit)

                uploaded_objs.append(obj)
        except Exception as e:
            for o in uploaded_objs:
                try:
                    osconn = osapi.os_connect()
                    osconn.object_store.delete_object(o)
                except:
                    pass
            raise e

        manifest_data = json.dumps([
            {
                'path': o.container + '/' + o.name,
                'etag': o.etag,
            } for o in uploaded_objs
        ])

        try:
            osconn = osapi.os_connect()
            obj = retry_call(osconn.object_store.upload_object, fkwargs={
                "container": config.get('DEFAULT', 'container-backups'),
                "name": user_name + '/' + time_string + '/' + file_name + '?multipart-manifest=put',
                "data": manifest_data}, tries=3)
        except Exception as e:
            for o in uploaded_objs:
                try:
                    osconn = osapi.os_connect()
                    osconn.object_store.delete_object(o)
                except:
                    pass
            raise e

        try:
            osconn = osapi.os_connect()
            osconn.object_store.set_object_metadata(obj,
                                                    container=config.get('DEFAULT', 'container-backups'),
                                                    username=user_name,
                                                    backup_time=time_string)
        except HttpException:
            # We don't really need metadata that much, it's not worth aborting the whole backup
            pass

    # Remove uploaded backup file now
    os.remove(os.environ.get('file'))

    # Notify CIAPI
    s = ciapi.get_session()
    r = s.post(config.get('DEFAULT', 'api_base_url') + 'system/directadmin/user_backup_post', json={
        'username': user_name,
        'backup_filename': file_name,
        'backup_datetime': time_string,
        'backup_size': backup_info.st_size,
        'backup_path': user_name + '/' + time_string + '/' + file_name,
    }, timeout=config.getint('DEFAULT', 'api_timeout'))

    if r.status_code != 200:
        print(r.json().get('message', None))
        exit(1)


@retry(HttpException, tries=3, delay=10)
def upload_file(local, remote, start=None, limit=None):
    if start is not None or limit is not None:
        c = config.get('DEFAULT', 'container-backups-segments')
    else:
        c = config.get('DEFAULT', 'container-backups')

    with open(local, 'rb') as f:
        if start is not None:
            f.seek(start)
        if limit is not None:
            f = LengthWrapper(f, limit, md5=False)

        logging.info('Starting upload of ' + remote)
        osconn = osapi.os_connect()
        return osconn.object_store.upload_object(container=c, name=remote, data=f, content_type='application/x-gzip')
