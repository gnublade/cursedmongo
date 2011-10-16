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


def encoder(obj):
    return repr(obj) if isinstance(obj, (ObjectId, DBRef)) else str(obj)

def decoder(val):
    if isinstance(val, basestring):
        evalable_objects = (
            'ObjectId',
            'datetime.datetime',
            'DBRef',
        )
        if val.startswith(evalable_objects):
            val = eval(val)
    return val


class CollectionBrowser(object):

    palette = [
        ('focus', 'black', 'yellow'),
    ]

    def __init__(self, db):
        self.db = db

    def main(self):
        self.collections = self.db.collection_names()
        collection_walker = urwid.SimpleListWalker(
            [urwid.AttrMap(w, None, 'focus')
             for w in [SelectableText(n) for n in self.collections]])
        self.collection_listbox = urwid.ListBox(collection_walker)
        self.documents = [urwid.Text("No Collection Selected")]
        self.document_walker = urwid.PollingListWalker(self.documents)
        self.document_listbox = urwid.ListBox(self.document_walker)

        self.columns = urwid.Columns([self.collection_listbox])
        self.loop = urwid.MainLoop(self.columns, self.palette,
                                   unhandled_input=self.unhandled_input)
        self.loop.run()

    def unhandled_input(self, key):
        if key == 'q':
            raise urwid.ExitMainLoop()

        wid = self.columns.get_focus()

        if key == 'enter':
            idx = self.columns.get_focus_column()
            self.columns.widget_list[idx + 1:] = []
            if wid == self.collection_listbox:
                name = self.collections[wid.get_focus()[1]]
                self.display_collection(name)
            elif wid == self.document_listbox:
                selected_item = self.document_listbox.get_focus()[0]
                pk = decoder(selected_item.original_widget.get_text()[0])
                self.display_document(pk)
            else:
                self.document_textbox.set_caption("%s\n" % wid)

        if key == 's':
            self.save_document()

        return key

    def display_collection(self, name):
        self.selected_collection = self.db[name]
        self.columns.widget_list.append(self.document_listbox)
        self.documents[:] = [
            urwid.AttrMap(w, None, 'focus')
            for w in [SelectableText(encoder(d['_id']))
                for d in self.selected_collection.find()]
        ]

    def display_document(self, pk):
        doc_textbox = urwid.Edit("", multiline=True, allow_tab=True)
        self.columns.widget_list.append(
            urwid.Filler(doc_textbox, valign='top'))
        doc = self.selected_collection.find_one({'_id': pk})
        text = json.dumps(doc, indent=4, default=encoder)
        doc_textbox.set_edit_text(text)

    def save_document(self):
        def object_hook(d):
            for key, val in d.items():
                d[key] = decoder(val)
            return d
        textbox = self.columns.get_focus()
        text = textbox.get_edit_text()
        doc = json.loads(text, object_hook=object_hook)
        self.selected_collection.save(doc)
        self.display_document(doc['_id'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('database')
    parser.add_argument('--host', default='localhost',
                        help='server to connect to')
    parser.add_argument('--port', type=int, default=27017,
                        help='port to connect to')
    args = parser.parse_args()

    conn = pymongo.Connection(args.host, args.port)
    db = conn[args.database]
    try:
        CollectionBrowser(db).main()
    except KeyboardInterrupt:
        pass
