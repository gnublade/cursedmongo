from mock import MagicMock, Mock
from unittest2 import TestCase

from bson.objectid import ObjectId
from pymongo.database import Database

from cursedmongo import CollectionBrowser


class MockCollection(MagicMock):

    def __init__(self, documents, *args, **kwargs):
        super(MockCollection, self).__init__(*args, **kwargs)
        self.documents = documents

    def find(self):
        return iter(self.documents)


class CollectionBrowserTest(TestCase):

    def _create_browser(self, collections):
        db = MagicMock(wraps=collections)
        db.__class__ = Database
        db.collection_names = Mock(return_value=collections.keys())
        db.__getitem__ = lambda s, x: MockCollection(collections[x])
        browser = CollectionBrowser(db)
        return browser

    def _get_columns(self, b):
        return list(b.columns.contents)

    def _get_contents(self, b, position=0):
        c = self._get_columns(b)
        return c[position][0].body.contents

    def _select_collection(self, b, position=0):
        c = self._get_contents(b)
        c.set_focus(position)
        b.unhandled_input('enter')

    def _render(self, b, size=(80, 25)):
        return b.columns.render(size)

    def _print(self, b):
        canvas = self._render(b)
        print "\n" + "\n".join(canvas.text) + "\n"

    def test_init_empty(self):
        browser = self._create_browser({})
        columns = self._get_columns(browser)
        self.assertEqual(len(columns), 1)
        collections = self._get_contents(browser)
        self.assertEqual(len(collections), 0)

    def test_init_collections(self):
        browser = self._create_browser({'one': [], 'two': [], 'three': []})
        columns = self._get_columns(browser)
        self.assertEqual(len(columns), 1)
        collections = self._get_contents(browser)
        self.assertEqual(len(collections), 3)

    def test_selecting_a_collection(self):
        docs = [
            {'_id': ObjectId()},
            {'_id': ObjectId()},
            {'_id': ObjectId()},
            {'_id': ObjectId()},
            {'_id': ObjectId()},
        ]
        browser = self._create_browser({'one': [], 'two': docs, 'three': []})
        self._select_collection(browser, 1)
        self._render(browser)
        columns = self._get_columns(browser)
        self.assertEqual(len(columns), 2)
        documents = self._get_contents(browser, 1)
        self.assertEqual(len(documents), 5)
