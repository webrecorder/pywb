import os

import pytest

from pywb.manager.manager import CollectionsManager

VALID_WACZ_PATH = 'sample_archive/waczs/valid_example_1.wacz'
INVALID_WACZ_PATH = 'sample_archive/waczs/invalid_example_1.wacz'

TEST_COLLECTION_NAME = 'test-col'


class TestManager:
    def test_add_valid_wacz_unpacked(self, tmp_path):
        """Test if adding a valid wacz file to a collection succeeds"""
        manager = self.get_test_collections_manager(tmp_path)
        manager._add_wacz_unpacked(VALID_WACZ_PATH)
        assert 'valid_example_1-0.warc' in os.listdir(manager.archive_dir)
        assert manager.DEF_INDEX_FILE in os.listdir(manager.indexes_dir)
        with open(os.path.join(manager.indexes_dir, manager.DEF_INDEX_FILE), 'r') as f:
            assert '"filename": "valid_example_1-0.warc"' in f.read()

    def test_add_valid_wacz_unpacked_dupe_name(self, tmp_path):
        """Test if warc that already exists is renamed with -index suffix"""
        manager = self.get_test_collections_manager(tmp_path)
        manager._add_wacz_unpacked(VALID_WACZ_PATH)
        # Add it again to see if there are name conflicts
        manager._add_wacz_unpacked(VALID_WACZ_PATH)
        assert 'valid_example_1-0.warc' in os.listdir(manager.archive_dir)
        assert 'valid_example_1-0-1.warc' in os.listdir(manager.archive_dir)
        assert manager.DEF_INDEX_FILE in os.listdir(manager.indexes_dir)
        with open(os.path.join(manager.indexes_dir, manager.DEF_INDEX_FILE), 'r') as f:
            data = f.read()
            assert '"filename": "valid_example_1-0.warc"' in data
            assert '"filename": "valid_example_1-0-1.warc"' in data

    def test_add_invalid_wacz_unpacked(self, tmp_path, caplog):
        """Test if adding an invalid wacz file to a collection fails"""
        manager = self.get_test_collections_manager(tmp_path)
        manager._add_wacz_unpacked(INVALID_WACZ_PATH)
        assert 'invalid_example_1-0.warc' not in os.listdir(manager.archive_dir)
        assert 'sample_archive/waczs/invalid_example_1.wacz does not contain any warc files.' in caplog.text

        index_path = os.path.join(manager.indexes_dir, manager.DEF_INDEX_FILE)
        if os.path.exists(index_path):
            with open(index_path, 'r') as f:
                assert '"filename": "invalid_example_1-0.warc"' not in f.read()

    def test_add_valid_archives_unpack_wacz(self, tmp_path):
        manager = self.get_test_collections_manager(tmp_path)
        archives = ['sample_archive/warcs/example.arc', 'sample_archive/warcs/example.arc.gz',
                    'sample_archive/warcs/example.warc', 'sample_archive/warcs/example.warc.gz',
                    'sample_archive/waczs/valid_example_1.wacz']
        manager.add_archives(archives, unpack_wacz=True)

        with open(os.path.join(manager.indexes_dir, manager.DEF_INDEX_FILE), 'r') as f:
            index_text = f.read()

        for archive in archives:
            archive = os.path.basename(archive)

            if archive.endswith('wacz'):
                archive = 'valid_example_1-0.warc'

            assert archive in os.listdir(manager.archive_dir)
            assert archive in index_text

    def test_add_valid_archives_dupe_name(self, tmp_path):
        manager = self.get_test_collections_manager(tmp_path)
        warc_filename = 'sample_archive/warcs/example.warc.gz'
        manager.add_archives([warc_filename, warc_filename])

        with open(os.path.join(manager.indexes_dir, manager.DEF_INDEX_FILE), 'r') as f:
            index_text = f.read()

        expected_archives = ('example.warc.gz', 'example-1.warc.gz')

        for archive in expected_archives:
            assert archive in os.listdir(manager.archive_dir)
            assert archive in index_text

    def test_add_valid_archives_dont_unpack_wacz(self, tmp_path):
        manager = self.get_test_collections_manager(tmp_path)
        archives = ['sample_archive/warcs/example.arc', 'sample_archive/warcs/example.arc.gz',
                    'sample_archive/warcs/example.warc', 'sample_archive/warcs/example.warc.gz',
                    'sample_archive/waczs/valid_example_1.wacz']

        with pytest.raises(NotImplementedError):
            manager.add_archives(archives, unpack_wacz=False)

    def test_add_invalid_archives_unpack_wacz(self, tmp_path, caplog):
        manager = self.get_test_collections_manager(tmp_path)
        manager.add_archives(['sample_archive/warcs/example.warc', 'sample_archive/text_content/sample.html'],
                             unpack_wacz=True)
        assert 'sample.html' not in os.listdir(manager.archive_dir)
        assert 'example.warc' in os.listdir(manager.archive_dir)
        assert "Invalid archives weren't added: sample_archive/text_content/sample.html" in caplog.messages

    def test_merge_wacz_index(self, tmp_path):
        manager = self.get_test_collections_manager(tmp_path)
        manager._add_wacz_index(os.path.join(manager.indexes_dir, manager.DEF_INDEX_FILE),
                                'sample_archive/cdxj/example.cdxj',
                                {'example.warc.gz': 'rewritten.warc.gz'})
        with open(os.path.join(manager.indexes_dir, manager.DEF_INDEX_FILE), 'r') as f:
            index_content = f.read()
            index_content = index_content.strip()

        assert 'example.warc.gz' not in index_content
        assert 'rewritten.warc.gz' in index_content

        # check that collection index is sorted
        index_lines = index_content.split('\n')
        assert sorted(index_lines) == index_lines

    def test_merge_wacz_index_gzip(self, tmp_path):
        manager = self.get_test_collections_manager(tmp_path)
        manager._add_wacz_index(os.path.join(manager.indexes_dir, manager.DEF_INDEX_FILE),
                                'sample_archive/cdxj/example.cdx.gz',
                                {'example-collection.warc': 'rewritten.warc'})
        with open(os.path.join(manager.indexes_dir, manager.DEF_INDEX_FILE), 'r') as f:
            index_content = f.read()
            index_content = index_content.strip()

        assert 'example-collection.warc' not in index_content
        assert 'rewritten.warc' in index_content

        # check that collection index is sorted
        index_lines = index_content.split('\n')
        assert sorted(index_lines) == index_lines

    @staticmethod
    def get_test_collections_manager(collections_path):
        manager = CollectionsManager(TEST_COLLECTION_NAME, colls_dir=collections_path, must_exist=False)
        manager.add_collection()
        return manager
