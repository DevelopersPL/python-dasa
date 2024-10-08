import logging
import os
import time

from fabric import Connection
from openstack.cloud._object_store import ObjectStoreCloudMixin
from six.moves import urllib_parse

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

    try:
        if config.getboolean('DEFAULT', 'backups_upload_swift'):
            c = os_connect()
            start_time = time.perf_counter()
            c.create_object(container=config.get('DEFAULT', 'backups_container'),
                            name=user_name + '/' + time_string + '/' + file_name,
                            filename=os.environ.get('file'),
                            segment_size=segment_limit,  # optional, should auto-discover
                            metadata={
                                'username': user_name,
                                'backup_time': time_string
                            },
                            generate_checksums=False,
                            **{'content-type': 'application/x-gzip'})

            # Print timing
            elapsed = time.perf_counter() - start_time
            size = utils.sizeof_fmt(backup_info.st_size / elapsed)
            logging.info('Swift upload of %s finished in %d seconds (%s/s)' % (file_name, elapsed, size))

        if config.getboolean('DEFAULT', 'backups_upload_ssh'):
            start_time = time.perf_counter()
            with Connection(config.get('DEFAULT', 'backups_ssh_host')) as c:
                c.put(os.environ.get('file'), remote=config.get('DEFAULT', 'backups_ssh_path'))

            # Print timing
            elapsed = time.perf_counter() - start_time
            size = utils.sizeof_fmt(backup_info.st_size / elapsed)
            logging.info('SSH upload of %s finished in %d seconds (%s/s)' % (file_name, elapsed, size))

        if config.getboolean('DEFAULT', 'backups_remove_local'):
            # Remove local backup file now
            os.remove(os.environ.get('file'))

        # Read log file if available
        log_file_content = None
        try:
            with open(config.get('DEFAULT', 'backups_post_log_file'), 'r') as f:
                log_file_content = f.read()
        except OSError:
            pass

        if config.getboolean('DEFAULT', 'backups_post_ciapi'):
            # Report to CIAPI
            s = ciapi.get_session()
            r = s.post('system/directadmin/user_backup_post', json={
                'username': user_name,
                'backup_filename': file_name,
                'backup_datetime': time_string,
                'backup_size': backup_info.st_size,
                'backup_path': user_name + '/' + time_string + '/' + file_name,
                'container': config.get('DEFAULT', 'backups_container'),
                'log': log_file_content,
            }, )

            if r.status_code != 200:
                logging.error(r.json().get('message', None))
                exit(1)
    except Exception as e:
        utils.plog(logging.ERROR, e, exc_info=True)
        if hasattr(e, 'response'):
            logging.error('Wystąpił błąd: %s - %s' % (e, e.response.text))
        else:
            logging.error('Wystąpił błąd: %s' % e)

        try:
            os.remove(os.environ.get('file'))
        except FileNotFoundError:
            pass

        exit(2)


# the original passes urlencoded path in SLO manifest, which is incorrect
def _upload_large_object(
        self, endpoint, filename,
        headers, file_size, segment_size, use_slo):
    # If the object is big, we need to break it up into segments that
    # are no larger than segment_size, upload each of them individually
    # and then upload a manifest object. The segments can be uploaded in
    # parallel, so we'll use the async feature of the TaskManager.

    segment_futures = []
    segment_results = []
    retry_results = []
    retry_futures = []
    manifest = []

    # Get an OrderedDict with keys being the swift location for the
    # segment, the value a FileSegment file-like object that is a
    # slice of the data for the segment.
    segments = self._get_file_segments(
        endpoint, filename, file_size, segment_size)

    # Schedule the segments for upload
    for name, segment in segments.items():
        # Async call to put - schedules execution and returns a future
        segment_future = self._pool_executor.submit(
            self.object_store.put,
            name, headers=headers, data=segment,
            raise_exc=False)
        segment_futures.append(segment_future)
        # TODO(mordred) Collect etags from results to add to this manifest
        # dict. Then sort the list of dicts by path.
        manifest.append(dict(
            path='/{name}'.format(name=urllib_parse.unquote(name)),
            size_bytes=segment.length))

    # Try once and collect failed results to retry
    segment_results, retry_results = self._wait_for_futures(
        segment_futures, raise_on_error=False)

    self._add_etag_to_manifest(segment_results, manifest)

    for result in retry_results:
        # Grab the FileSegment for the failed upload so we can retry
        name = self._object_name_from_url(result.url)
        segment = segments[name]
        segment.seek(0)
        # Async call to put - schedules execution and returns a future
        segment_future = self._pool_executor.submit(
            self.object_store.put,
            name, headers=headers, data=segment)
        # TODO(mordred) Collect etags from results to add to this manifest
        # dict. Then sort the list of dicts by path.
        retry_futures.append(segment_future)

    # If any segments fail the second time, just throw the error
    segment_results, retry_results = self._wait_for_futures(
        retry_futures, raise_on_error=True)

    self._add_etag_to_manifest(segment_results, manifest)

    # If the final manifest upload fails, remove the segments we've
    # already uploaded.
    try:
        if use_slo:
            return self._finish_large_object_slo(endpoint, headers,
                                                 manifest)
        else:
            return self._finish_large_object_dlo(endpoint, headers)
    except Exception:
        try:
            segment_prefix = endpoint.split('/')[-1]
            self.log.debug(
                "Failed to upload large object manifest for %s. "
                "Removing segment uploads.", segment_prefix)
            self.delete_autocreated_image_objects(
                segment_prefix=segment_prefix)
        except Exception:
            self.log.exception(
                "Failed to cleanup image objects for %s:",
                segment_prefix)
        raise


ObjectStoreCloudMixin._upload_large_object = _upload_large_object
