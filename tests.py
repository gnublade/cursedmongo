
from mock import Mock
from unittest2 import TestCase

from cursedmongo import CollectionBrowser


class CollectionBrowserTest(TestCase):

    def create_browser(self, collections):
        db = Mock()
        db.collection_names.return_value = collections.keys()
        browser = CollectionBrowser(db)
        return browser

    def get_columns(self, b):
        return list(b.contents)

    def get_collections(self, c, idx=0):
        return c[idx][0].body.contents

    def test_init_empty(self):
        browser = self.create_browser({})
        columns = self.get_columns(browser.columns)
        self.assertEqual(len(columns), 1)
        collections = self.get_collections(columns)
        self.assertEqual(len(collections), 0)

    def test_init_collections(self):
        browser = self.create_browser({'one': {}, 'two': {}, 'three': {}})
        columns = self.get_columns(browser.columns)
        self.assertEqual(len(columns), 1)
        collections = self.get_collections(columns)
        self.assertEqual(len(collections), 3)
