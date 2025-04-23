from .testutils import TempDirTests, BaseTestClass
from pywb.warcserver.warcserver import WarcServer
import os

from pywb.warcserver.index.indexsource import RemoteIndexSource, LiveIndexSource, MementoIndexSource
from pywb.warcserver.index.indexsource import WBMementoIndexSource, FileIndexSource
from pywb.warcserver.index.aggregator import BaseSourceListAggregator, DirectoryIndexSource
from pywb.warcserver.handlers import ResourceHandler, HandlerSeq


# ============================================================================
class TestWarcServer(TempDirTests, BaseTestClass):
    @classmethod
    def setup_class(cls):
        super(TestWarcServer, cls).setup_class()
        cls.orig_cwd = os.getcwd()
        os.chdir(cls.root_dir)
        os.mkdir('./local')
        os.mkdir('./local/indexes')

        os.mkdir('collections')
        os.mkdir('collections/auto1')
        os.mkdir('collections/auto2')

        with open(os.path.join('local', 'indexes', 'file.cdxj'), 'a') as fh:
            fh.write('foo')

        with open(os.path.join('local', 'indexes', 'file.idx'), 'a') as fh:
            fh.write('foo')

        with open(os.path.join('local', 'indexes', 'file.loc'), 'a') as fh:
            fh.write('foo')

        cls.loader = WarcServer(os.path.join(cls.get_curr_dir(), 'test_warcserver_config.yaml'))

    @classmethod
    def teardown_class(cls):
        os.chdir(cls.orig_cwd)
        super(TestWarcServer, cls).teardown_class()

    @staticmethod
    def get_curr_dir():
        return os.path.dirname(os.path.realpath(__file__))

    def _get_sources(self, coll_name='', handler=None):
        if not handler:
            handler = self.loader.fixed_routes.get(coll_name)
        assert isinstance(handler, ResourceHandler)
        assert isinstance(handler.index_source, BaseSourceListAggregator)
        return handler.index_source.sources

    def test_list_static(self):
        assert len(self.loader.list_fixed_routes()) == 13

    def test_list_dynamic(self):
        assert set(self.loader.list_dynamic_routes()) == set(['auto1', 'auto2'])

    def test_remote_cdx(self):
        sources = self._get_sources('ait')
        assert isinstance(sources['ait'], RemoteIndexSource)
        assert sources['ait'].api_url == 'http://wayback.archive-it.org/cdx?url={url}&closest={closest}&sort=closest'
        assert sources['ait'].replay_url == 'http://wayback.archive-it.org/all/{timestamp}id_/{url}'

        long_form_sources = self._get_sources('ait_long')
        assert sources['ait'] == long_form_sources['ait_long']

    def test_memento(self):
        sources = self._get_sources('rhiz')
        assert isinstance(sources['rhiz'], MementoIndexSource)
        assert sources['rhiz'].timegate_url == 'http://webarchives.rhizome.org/all/{url}'
        assert sources['rhiz'].timemap_url == 'http://webarchives.rhizome.org/all/timemap/link/{url}'
        assert sources['rhiz'].replay_url == 'http://webarchives.rhizome.org/all/{timestamp}id_/{url}'

        long_form_sources = self._get_sources('rhiz_long')
        assert sources['rhiz'] == long_form_sources['rhiz_long']

    def test_wb_memento(self):
        sources = self._get_sources('rhiz_wb')
        assert isinstance(sources['rhiz_wb'], WBMementoIndexSource)
        assert sources['rhiz_wb'].timegate_url == 'http://webarchives.rhizome.org/all/{url}'
        assert sources['rhiz_wb'].timemap_url == 'http://webarchives.rhizome.org/all/timemap/link/{url}'
        assert sources['rhiz_wb'].replay_url == 'http://webarchives.rhizome.org/all/{timestamp}im_/{url}'
        assert sources['rhiz_wb'].prefix == 'http://webarchives.rhizome.org/all/'

    def test_remote_cdx_2(self):
        sources = self._get_sources('rhiz_cdx')
        assert isinstance(sources['rhiz_cdx'], RemoteIndexSource)
        assert sources['rhiz_cdx'].api_url == 'http://webarchives.rhizome.org/all-cdx?url={url}&closest={closest}&sort=closest'
        assert sources['rhiz_cdx'].replay_url == 'http://webarchives.rhizome.org/all/{timestamp}id_/{url}'

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
        seq = self.loader.fixed_routes.get('many_seq')
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

