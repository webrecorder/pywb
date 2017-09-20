import gevent
import time
import re
import os
import logging

from pywb.manager.manager import CollectionsManager


#=============================================================================
class AutoIndexer(object):
    EXT_RX = re.compile('.*\.w?arc(\.gz)?$')
    AUTO_INDEX_FILE = 'autoindex.cdxj'

    def __init__(self, interval=30, keep_running=True):
        self.manager = CollectionsManager('', must_exist=False)

        self.root_path = self.manager.colls_dir

        self.keep_running = keep_running

        self.interval = interval

    def is_newer_than(self, path1, path2):
        try:
            mtime1 = os.path.getmtime(path1)
            mtime2 = os.path.getmtime(path2)
            return mtime1 > mtime2
        except:
            return True

    def do_index(self, files):
        logging.info('Auto-Indexing... ' + str(files))
        self.manager.index_merge(files, self.AUTO_INDEX_FILE)
        logging.info('...Done')

    def check_path(self):
        for coll in os.listdir(self.root_path):
            coll_dir = os.path.join(self.root_path, coll)
            if not os.path.isdir(coll_dir):
                continue

            self.manager.change_collection(coll)

            archive_dir = self.manager.archive_dir

            if not os.path.isdir(archive_dir):
                continue

            index_file = os.path.join(self.manager.indexes_dir, self.AUTO_INDEX_FILE)

            if os.path.isfile(index_file):
                if self.is_newer_than(archive_dir, index_file):
                    continue
            else:
                try:
                    os.makedirs(self.manager.indexes_dir)
                except Exception as e:
                    pass

            logging.info('Collection Possibly Changed: ' + coll)
            to_index = []
            for dirpath, dirnames, filenames in os.walk(archive_dir):
                for filename in filenames:
                    if not self.EXT_RX.match(filename):
                        continue

                    full_filename = os.path.join(dirpath, filename)

                    if self.is_newer_than(full_filename, index_file):
                        to_index.append(full_filename)

            if to_index:
                self.do_index(to_index)

    def run(self):
        try:
            while self.keep_running:
                self.check_path()
                if not self.interval:
                    break

                time.sleep(self.interval)
        except KeyboardInterrupt:  # pragma: no cover
            return

    def start(self):
        self.ge = gevent.spawn(self.run)

    def stop(self):
        self.interval = 0
        self.keep_running = False

