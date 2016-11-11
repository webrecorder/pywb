import gevent
import time
import re
import os


#=============================================================================
EXT_RX = re.compile('.*\.w?arc(\.gz)?$')

keep_running = True


#=============================================================================
class CDXAutoIndexer(object):
    def __init__(self, updater, path):
        self.updater = updater
        self.root_path = path

        self.mtimes = {}

    def has_changed(self, *paths):
        full_path = os.path.join(*paths)
        try:
            mtime = os.path.getmtime(full_path)
        except:
            return False

        if mtime == self.mtimes.get(full_path):
            return False

        self.mtimes[full_path] = mtime
        return full_path

    def check_path(self):
        for dirName, subdirList, fileList in os.walk(self.root_path):
            if not subdirList and not self.has_changed(dirName):
                return False

            for filename in fileList:
                if not EXT_RX.match(filename):
                    continue

                path = self.has_changed(self.root_path, dirName, filename)
                if not path:
                    continue

                self.updater(os.path.join(dirName, filename))

    def do_loop(self, interval):
        try:
            while keep_running:
                self.check_path()
                time.sleep(interval)
        except KeyboardInterrupt:  # pragma: no cover
            return

    def start(self, interval):
        self.ge = gevent.spawn(self.do_loop, interval)


