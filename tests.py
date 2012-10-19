
from mock import Mock
from unittest2 import TestCase

from cursedmongo import CollectionBrowser

class CollectionBrowserTest(TestCase):
    def test_init(self):
        db = Mock()
        CollectionBrowser(db)
