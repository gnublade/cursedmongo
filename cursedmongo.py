#!/usr/bin/env python

import argparse
import datetime
import pymongo
import urwid

from pymongo.database import Database
from pymongo.collection import Collection
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

def object_hook(d):
    for key, val in d.items():
        d[key] = decoder(val)
    return d

class CollectionBrowser(object):

    palette = [
        ('focus', 'black', 'yellow'),
    ]

    def __init__(self, db):
        self.db = db

    def main(self):
        self.stack = [self.db]
        self.collections = self.db.collection_names()
        collection_walker = urwid.SimpleListWalker(
            [urwid.AttrMap(w, None, 'focus')
             for w in [SelectableText(n) for n in self.collections]])
        self.collection_listbox = urwid.ListBox(collection_walker)
        self.documents = [urwid.Text("No Collection Selected")]
        self.document_walker = urwid.PollingListWalker(self.documents)
        self.document_listbox = urwid.ListBox(self.document_walker)

        self.columns = urwid.Columns([self.collection_listbox], dividechars=1)
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
            self.stack[idx + 1:] = []
            parent = self.stack[idx]

            if isinstance(parent, Database):
                # Collection selected
                name = self.collections[wid.get_focus()[1]]
                collection = parent[name]
                self.stack.append({'collection': collection})
                self.display_collection(collection)

            elif 'values' in parent:
                # Item in a dict or schema
                selected_item = wid.get_focus()[0]
                selected_text = selected_item.original_widget.get_text()[0]
                key = selected_text.split(':')[0]
                values = parent['values'][key]
                self.stack.append({
                    'collection': parent['collection'],
                    'document': parent['document'],
                    'values': values,
                })
                if isinstance(values, dict):
                    self.display_document(values)
                elif isinstance(values, list):
                    self.display_list(values)
                else:
                    selected_item = wid.get_focus()[0].original_widget
                    if isinstance(selected_item, urwid.Edit):
                        text = selected_item.get_edit_text()
                        key = selected_item.get_caption()[:-1]
                        # Save the owner document.
                        value = json.loads(text, object_hook=object_hook)
                        parent['values'][key] = text
                        #parent['collection'].save(parent['document'])
                        textbox = urwid.SelectableText("%s: %s" % (
                            encoder(n), json.dumps(v, default=encoder)), wrap='clip')
                    else:
                        text = selected_item.get_text()[0]
                        name, sep, value = text.partition(':')
                        textbox = urwid.Edit("%s:" % name, value)
                    selected_item.original_widget = textbox

            elif 'collection' in parent:
                # Document selected
                selected_item = wid.get_focus()[0]
                pk = decoder(selected_item.original_widget.get_text()[0])
                doc = parent['collection'].find_one({'_id': pk})
                self.stack.append({
                    'collection': parent['collection'],
                    'document': doc,
                    'values': doc,
                })
                self.display_document(doc)

            else:
                selected_item = wid.get_focus()[0]
                text = selected_item.original_widget.get_text()[0]
                selected_item.original_widget = urwid.Edit(edit_text=text)

        if key == 's':
            self.save_document()

        return key

    def display_collection(self, collection):
        self.columns.widget_list.append(self.document_listbox)
        self.documents[:] = [
            urwid.AttrMap(w, None, 'focus')
            for w in [SelectableText(encoder(d['_id']))
                for d in collection.find()]
        ]

    def display_document(self, doc):
        schema_walker = urwid.PollingListWalker([
            urwid.AttrMap(w, None, 'focus')
            for w in [SelectableText("%s: %s" % (
                encoder(n), json.dumps(v, default=encoder)), wrap='clip')
                for (n, v) in doc.items()]])
        schema_listbox = urwid.ListBox(schema_walker)
        #doc_textbox = urwid.Edit("", multiline=True, allow_tab=True)
        self.columns.widget_list.append(schema_listbox)
            #urwid.Filler(doc_textbox, valign='top'))
        #text = json.dumps(doc, indent=4, default=encoder)
        #doc_textbox.set_edit_text(text)

    def display_list(self, values):
        list_walker = urwid.PollingListWalker([
            urwid.AttrMap(w, None, 'focus')
            for w in [SelectableText(json.dumps(v, default=encoder), wrap='clip')
                for v in values]])
        list_listbox = urwid.ListBox(list_walker)
        self.columns.widget_list.append(list_listbox)

    def save_document(self):
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
