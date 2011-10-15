#!/usr/bin/env python

import argparse
import datetime
import pymongo
import urwid

from pymongo.dbref import DBRef
from pymongo.objectid import ObjectId

try:
    import json
except ImportError:
    import simplejson as json

from pprint import pformat

class SelectableText(urwid.Text):

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key


class CollectionBrowser(object):

    palette = [
        ('focus', 'black', 'yellow'),
    ]

    def __init__(self, database):
        conn = pymongo.Connection()
        self.db = conn[database]

    def main(self):
        self.collections = self.db.collection_names()
        collection_walker = urwid.SimpleListWalker(
            [urwid.AttrMap(w, None, 'focus')
             for w in [SelectableText(n) for n in self.collections]])
        self.collection_listbox = urwid.ListBox(collection_walker)
        self.documents = [urwid.Text("No Collection Selected")]
        self.document_walker = urwid.PollingListWalker(self.documents)
        self.document_listbox = urwid.ListBox(self.document_walker)
        self.document_textbox = urwid.Edit("", multiline=True, allow_tab=True)
        self.document_columns = urwid.Columns([
            self.document_listbox,
            urwid.Filler(self.document_textbox, valign='top'),
        ])
        self.pile = urwid.Pile([
            self.collection_listbox,
            self.document_columns,
        ])
        self.loop = urwid.MainLoop(self.pile, self.palette,
                                   unhandled_input=self.unhandled_input)
        self.loop.run()

    def unhandled_input(self, key):
        if key == 'q':
            raise urwid.ExitMainLoop()

        wid = self.get_focused_widget()

        if key == 'enter':
            if wid == self.collection_listbox:
                name = self.collections[wid.get_focus()[1]]
                self.display_collection(name)
            elif wid == self.document_listbox:
                selected_item = self.document_listbox.get_focus()[0]
                pk = eval(selected_item.original_widget.get_text()[0])
                self.document_textbox.set_caption('%s\n' % pk)
                self.display_document(pk)
            else:
                self.document_textbox.set_caption("%s\n" % wid)

        if key == 's':
            self.save_document()

        return key

    def get_focused_widget(self):
        wid = self.pile.get_focus()
        if wid == self.document_columns:
            wid = self.document_columns.get_focus()
        return wid

    def display_collection(self, name):
        self.selected_collection = self.db[name]
        self.documents[:] = [
            urwid.AttrMap(w, None, 'focus')
            for w in [SelectableText(repr(d['_id']))
                for d in self.selected_collection.find()]
        ]

    def display_document(self, pk):
        def encoder(obj):
            return repr(obj)
        doc = self.selected_collection.find_one({'_id': pk})
        text = json.dumps(doc, indent=4, default=encoder)
        self.document_textbox.set_edit_text(text)

    def save_document(self):
        def decoder(d):
            for key, val in d.items():
                if isinstance(val, basestring):
                    evalable_objects = (
                        'ObjectId',
                        'datetime.datetime',
                        'DBRef',
                    )
                    if val.startswith(evalable_objects):
                        d[key] = eval(val)
            return d
        text = self.document_textbox.get_edit_text()
        doc = json.loads(text, object_hook=decoder)
        self.selected_collection.save(doc)
        self.display_document(doc['_id'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('database')
    args = parser.parse_args()
    try:
        CollectionBrowser(args.database).main()
    except KeyboardInterrupt:
        pass
