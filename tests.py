from collections import OrderedDict

from mock import MagicMock, Mock
from unittest2 import TestCase

from bson.objectid import ObjectId
from pymongo import Connection
from pymongo.database import Database

from cursedmongo import CollectionBrowser


class MockCollection(MagicMock):

    def __init__(self, documents, *args, **kwargs):
        super(MockCollection, self).__init__(*args, **kwargs)
        self.documents = documents

    def find(self):
        return iter(self.documents)


class CollectionBrowserTest(TestCase):

    def _create_database(self, collections):
        collections = OrderedDict(collections)
        db = MagicMock(spec=Database)
        db.collection_names = Mock(return_value=collections.keys())
        db.__getitem__ = lambda s, x: MockCollection(collections[x])
        return db

    def _create_connection(self, databases):
        databases = OrderedDict(databases)
        connection = MagicMock(spec=Connection)
        connection.database_names = Mock(return_value=databases.keys())
        connection.__getitem__ = lambda s, x: databases[x]
        return connection

    def _create_browser(self, collections=None, databases=None, name=None):
        if databases is None:
            databases = {'test': self._create_database(collections)}
            name = 'test'
        connection = self._create_connection(databases)
        browser = CollectionBrowser(connection, name)
        return browser

    def _get_columns(self, b):
        return list(b.columns.contents)

    def _get_contents(self, b, position=0):
        c = self._get_columns(b)
        return c[position][0].body.contents

    def _select_item(self, b, position=0):
        c = self._get_contents(b)
        c.set_focus(position)
        b.unhandled_input('enter')

    def _render(self, b, size=(80, 25)):
        return b.columns.render(size)

    def _print(self, b):
        canvas = self._render(b)
        print "\n" + "\n".join(canvas.text) + "\n"

    def test_browse_databases_empty(self):
        databases = {}
        browser = self._create_browser(databases=databases)
        columns = self._get_columns(browser)
        self.assertEqual(len(columns), 1)
        collections = self._get_contents(browser)
        self.assertEqual(len(collections), 0)

    def test_browse_databases(self):
        databases = {
            'postgres': self._create_database({}),
            'mysql': self._create_database({}),
            'mongodb': self._create_database({}),
        }
        browser = self._create_browser(databases=databases)
        columns = self._get_columns(browser)
        self.assertEqual(len(columns), 1)
        collections = self._get_contents(browser)
        self.assertEqual(len(collections), 3)

    def test_select_database(self):
        mongodb = self._create_database(
            (c, []) for c in ('one', 'two', 'three', 'four')
        )
        databases = [
            ('postgres', self._create_database({})),
            ('mysql', self._create_database({})),
            ('mongodb', mongodb),
        ]
        browser = self._create_browser(databases=databases)
        self._select_item(browser, 2)  # Mongo
        self._render(browser)

        columns = self._get_columns(browser)
        self.assertEqual(len(columns), 1)
        collections = self._get_contents(browser)
        self.assertEqual(len(collections), 4)

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
        self._select_item(browser, 1)
        self._render(browser)
        columns = self._get_columns(browser)
        self.assertEqual(len(columns), 2)
        documents = self._get_contents(browser, 1)
        self.assertEqual(len(documents), 5)

    def test_changing_selected_collection(self):
        browser = self._create_browser([
            ('one', [{'_id': "document_in_collection_one"}]),
            ('two', [{'_id': "document_in_collection_two"}]),
        ])
        self._select_item(browser, 0)
        self._select_item(browser, 1)
        self._render(browser)
        documents = self._get_contents(browser, 1)
        self.assertEqual(documents[0]['_id'], "document_in_collection_two")
