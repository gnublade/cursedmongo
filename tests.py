
from mock import Mock
from unittest2 import TestCase

from cursedmongo import CollectionBrowser

class CollectionBrowserTest(TestCase):

    def test_init_empty(self):
        db = Mock()
        db.collection_names.return_value = []
        CollectionBrowser(db)
