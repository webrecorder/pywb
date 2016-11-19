from .testutils import TempDirTests, BaseTestClass
from pywb.webagg.autoapp import AutoConfigApp
import os

from pywb.webagg.indexsource import RemoteIndexSource, LiveIndexSource, MementoIndexSource, FileIndexSource
from pywb.webagg.handlers import ResourceHandler, HandlerSeq
from pywb.webagg.aggregator import BaseSourceListAggregator, DirectoryIndexSource


# ============================================================================
class TestAutoConfigApp(TempDirTests, BaseTestClass):
    @classmethod
    def setup_class(cls):
        super(TestAutoConfigApp, cls).setup_class()
        cls.orig_cwd = os.getcwd()
        os.chdir(cls.root_dir)
        os.mkdir('./local')
        os.mkdir('./local/indexes')

        with open(os.path.join('local', 'indexes', 'file.cdxj'), 'a') as fh:
            fh.write('foo')

        with open(os.path.join('local', 'indexes', 'file.idx'), 'a') as fh:
            fh.write('foo')

        with open(os.path.join('local', 'indexes', 'file.loc'), 'a') as fh:
            fh.write('foo')

        cls.loader = AutoConfigApp(os.path.join(cls.get_curr_dir(), 'test_autoapp.yaml'))

        cls.colls = cls.loader.load_colls()

    @classmethod
    def teardown_class(cls):
        os.chdir(cls.orig_cwd)
        super(TestAutoConfigApp, cls).teardown_class()

    @staticmethod
    def get_curr_dir():
        return os.path.dirname(os.path.realpath(__file__))

    def _get_sources(self, coll_name='', handler=None):
        if not handler:
            handler = self.colls.get(coll_name)
        assert isinstance(handler, ResourceHandler)
        assert isinstance(handler.index_source, BaseSourceListAggregator)
        return handler.index_source.sources

    def test_remote_cdx(self):
        sources = self._get_sources('ait')
        assert isinstance(sources['ait'], RemoteIndexSource)
        assert sources['ait'].api_url == 'http://wayback.archive-it.org/cdx?url={url}'
        assert sources['ait'].replay_url == 'http://wayback.archive-it.org/all/{timestamp}id_/{url}'

        long_form_sources = self._get_sources('ait_long')
        assert sources['ait'] == long_form_sources['ait_long']

    def test_memento(self):
        sources = self._get_sources('rhiz')
        assert isinstance(sources['rhiz'], MementoIndexSource)
        assert sources['rhiz'].timegate_url == 'http://webenact.rhizome.org/all/{url}'
        assert sources['rhiz'].timemap_url == 'http://webenact.rhizome.org/all/timemap/link/{url}'
        assert sources['rhiz'].replay_url == 'http://webenact.rhizome.org/all/{timestamp}id_/{url}'

        long_form_sources = self._get_sources('rhiz_long')
        assert sources['rhiz'] == long_form_sources['rhiz_long']

    def test_remote_cdx_2(self):
        sources = self._get_sources('rhiz_cdx')
        assert isinstance(sources['rhiz_cdx'], RemoteIndexSource)
        assert sources['rhiz_cdx'].api_url == 'http://webenact.rhizome.org/all-cdx?url={url}'
        assert sources['rhiz_cdx'].replay_url == 'http://webenact.rhizome.org/all/{timestamp}id_/{url}'

    def test_live(self):
        sources = self._get_sources('live')
        assert isinstance(sources['live'], LiveIndexSource)

    def test_index_group(self):
        sources = self._get_sources('many')
        assert isinstance(sources['ia'], RemoteIndexSource)
        assert isinstance(sources['rhiz'], MementoIndexSource)

    def test_local(self):
        # Directory exists
        sources = self._get_sources('local')
        assert isinstance(sources['local'], DirectoryIndexSource)

        # File exists
        sources = self._get_sources('local_file')
        assert isinstance(sources['local_file'], FileIndexSource)

    def test_sequence(self):
        seq = self.colls.get('many_seq')
        assert isinstance(seq, HandlerSeq)

        assert len(seq.handlers) == 3

        sources = self._get_sources(handler=seq.handlers[0])
        assert len(sources) == 1
        assert isinstance(sources['local'], DirectoryIndexSource)

        sources = self._get_sources(handler=seq.handlers[1])
        assert len(sources) == 2
        assert isinstance(sources['rhiz'], RemoteIndexSource)
        assert isinstance(sources['apt'], MementoIndexSource)

        sources = self._get_sources(handler=seq.handlers[2])
        assert len(sources) == 1
        assert isinstance(sources['live'], LiveIndexSource)







