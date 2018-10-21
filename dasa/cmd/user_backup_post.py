import requests

import json
import logging
import math
import os
import time

from openstack.exceptions import HttpException
from retry import retry
from retry.api import retry_call

from dasa import ciapi
from dasa.config import config
from dasa.config import os_connect
from dasa import utils

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

    # max object size is 5368709122 (5 GB + 2 bytes)
    if backup_info.st_size <= segment_limit:
        obj = upload_file(os.environ.get('file'), user_name + '/' + time_string + '/' + file_name)
    else:
        # We have to send multiple segments and create a Static Large Object manifest
        segments = int(math.ceil(backup_info.st_size / segment_limit))
        uploaded_objs = []

        try:
            for segment in range(segments):
                logging.info('Uploading segment %d', segment)
                if (segment + 1) * segment_limit > backup_info.st_size:
                    limit = backup_info.st_size % segment_limit
                else:
                    limit = segment_limit
                obj = upload_file(os.environ.get('file'),
                                  user_name + '/' + time_string + '/' + file_name + '/' + str(segment) + '.part',
                                  segment * segment_limit, limit)
                uploaded_objs.append(obj)

            # assemble manifest consisting of all segments
            manifest_data = json.dumps([
                {
                    'path': o.container + '/' + o.name,
                    'etag': o.etag,
                } for o in uploaded_objs
            ])

            # upload manifest
            c = os_connect()
            obj = retry_call(c.object_store.create_object, fkwargs={
                'container': config.get('DEFAULT', 'backups_container'),
                'name': user_name + '/' + time_string + '/' + file_name + '?multipart-manifest=put',
                'data': manifest_data,
                'content_type': 'application/x-gzip'
            }, tries=3)
        except Exception as e:
            # attempt to purge segments
            for o in uploaded_objs:
                try:
                    c = os_connect()
                    c.object_store.delete_object(o)
                except:
                    # failure is irrelevant
                    pass
            raise e

    # Try to set metadata on the obj
    try:
        c = os_connect()
        c.object_store.set_object_metadata(obj,
                                           container=config.get('DEFAULT', 'backups_container'),
                                           username=user_name,
                                           backup_time=time_string,
                                           content_type='application/x-gzip')  # fix for upload_file()
    except HttpException:
        # We don't really need metadata that much, it's not worth aborting the whole backup
        pass

    # Remove local backup file now
    os.remove(os.environ.get('file'))

    try:
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
    except requests.exceptions.RequestException as e:
        utils.plog(logging.ERROR, e, exc_info=True)
        logging.error('Wystąpił błąd: %s' % e)
        exit(2)


@retry(HttpException, tries=3, delay=60)
def upload_file(local, remote, start=None, limit=None):
    cn = config.get('DEFAULT', 'backups_container')

    with open(local, 'rb') as f:
        size = os.path.getsize(local)
        if start is not None:
            f.seek(start)
            size = size - start
        if limit is not None:
            f = utils.LengthWrapper(f, limit, md5=False)
            size = max(size, limit)

        logging.info('Starting upload of ' + remote)
        c = os_connect()
        start_time = time.clock()
        # content_type below does not seem to work, resulting content_type is text/html; charset=UTF-8
        obj = c.object_store.create_object(container=cn, name=remote, data=f, content_type='application/x-gzip')
        elapsed = time.clock() - start_time
        size = utils.sizeof_fmt(size / elapsed)
        logging.info('Upload of %s finished in %d seconds (%s)' % (remote, elapsed, size))
        return obj
