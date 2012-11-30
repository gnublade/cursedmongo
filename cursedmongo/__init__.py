#!/usr/bin/env python

import argparse
import json
import pymongo
import urwid

from bson.dbref import DBRef
from bson.objectid import ObjectId
from pymongo.database import Database


# Index into the columns
COLLECTION_COL = 0
DOCUMENT_COL = 1

CONNECTION_STACK_IDX = 0
DATABASE_STACK_IDX = 1
COLLECTION_STACK_IDX = 2
DOCUMENT_STACK_IDX = 3

class SelectableText(urwid.Text):
    """Selectable text widget."""

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key


def encoder(obj):
    """JSON encoder that can encode DBRefs."""
    return repr(obj) if isinstance(obj, (ObjectId, DBRef)) else str(obj)


def decoder(val):
    """JSON decoder that can decode pymongo types."""
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
    """Decodes the given JSON object using `decoder`."""
    for key, val in d.items():
        d[key] = decoder(val)
    return d


class GeneratorList(list):
    """Allows a generator to be (lazily) accessed as a list."""

    def __init__(self, generator):
        self._generator = generator

    def __getitem__(self, index):
        for _ in range(index - len(self) + 1):
            self.append(self._generator.next())
        return super(GeneratorList, self).__getitem__(index)


class DocumentWalker(urwid.ListWalker):
    """ListWalker-compatible class for browsing collections."""

    def __init__(self, contents):
        self.pos = 0
        self.contents = contents

    def _get_at_pos(self, pos):
        """Return a widget and the position passed."""
        try:
            doc = self.contents[pos]
            key = doc.get('_id') or doc.get('name', pos)
            widget = SelectableText(encoder(key))
            return urwid.AttrMap(widget, None, 'focus'), pos
        except StopIteration:
            return None, None

    def get_focus(self):
        return self._get_at_pos(self.pos)

    def set_focus(self, pos):
        self.pos = pos
        self._modified()

    def get_next(self, pos):
        return self._get_at_pos(pos + 1)

    def get_prev(self, pos):
        pos = pos - 1
        return (None, None) if pos < 0 else self._get_at_pos(pos)


class CollectionBrowser(object):
    """Main interface allowing browsing of collections and it's documents."""

    palette = [
        ('focus', 'black', 'yellow'),
        ('faint', 'light gray', 'default'),
    ]

    def __init__(self, connection, database=None):
        self.connection = connection
        self.databases = connection.database_names()
        self.stack = [self.connection]
        if database:
            self.stack_offset = 1
            self.select_database(self.connection[database])
            self.init_columns(self.collections)
        else:
            self.stack_offset = 0
            self.init_columns(self.databases)

    def init_columns(self, content):
        items = [SelectableText(n) for n in content]
        collection_listbox = self.create_column(items)
        self.columns = urwid.Columns([collection_listbox], dividechars=1)

    def create_column(self, items):
        # Decorate the items so that they can receive the focus palette.
        items = [urwid.AttrMap(w, None, 'focus') for w in items]
        list_walker = urwid.SimpleListWalker(items)
        column = urwid.ListBox(list_walker)
        return column

    def select_database(self, database):
        """Selects a database, deleting the remaining stack."""
        self.stack[DATABASE_STACK_IDX:] = [database]
        # The names of the collections in the database.
        self.collections = database.collection_names()
        self.stack_offset = 1

    def select_collection(self, collection):
        """Selects a collection, deleting the remaining stack."""
        self.stack[COLLECTION_STACK_IDX:] = [{'collection': collection}]

    def main(self):
        """Setup the urwid interface and run the eventloop."""
        self.loop = urwid.MainLoop(self.columns, self.palette,
                                   unhandled_input=self.unhandled_input)
        self.loop.run()

    def unhandled_input(self, key):
        """Any input not handled by urwid itself."""
        if key == 'q':
            raise urwid.ExitMainLoop()

        wid = self.columns.get_focus()

        if key == 'enter':
            self.select_item(wid)
        elif key == 's':
            self.save_document()

        return key

    def select_item(self, wid):
        """Expand (or edit) the currently selected item."""
        idx = self.columns.get_focus_column()
        self.columns.widget_list[idx + 1:] = []
        self.stack[idx + self.stack_offset + 1:] = []
        parent = self.stack[idx + self.stack_offset]

        if isinstance(parent, pymongo.Connection):
            # Database selected
            name = self.databases[wid.get_focus()[1]]
            database = parent[name]
            self.select_database(database)
            self.display_database(database)

        elif isinstance(parent, Database):
            # Collection selected
            name = self.collections[wid.get_focus()[1]]
            collection = parent[name]
            self.select_collection(collection)
            self.display_collection(collection)

        elif 'values' in parent:
            # Item in a dict or schema
            selected_item, selected_pos = wid.get_focus()
            selected_text = selected_item.original_widget.get_text()[0]
            key = selected_text.split(':')[0]
            if isinstance(parent['values'], list):
                values = parent['values'][selected_pos]
            else:
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
                    list_item_value = json.dumps(text, default=encoder)
                    list_item = "%s: %s" % (encoder(key), list_item_value)
                    textbox = urwid.SelectableText(list_item, wrap='clip')
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

    def display_database(self, database):
        items = [SelectableText(n) for n in self.collections]
        listbox = self.create_column(items)
        self.columns.widget_list[COLLECTION_COL:] = [listbox]

    def display_collection(self, collection):
        documents = GeneratorList(collection.find())
        document_walker = DocumentWalker(documents)
        document_listbox = urwid.ListBox(document_walker)
        self.columns.widget_list[DOCUMENT_COL:] = [document_listbox]

    def display_document(self, doc):
        items = [SelectableText([
            (None, encoder(n)),
            (None, ": "),
            ('faint', json.dumps(doc[n], default=encoder)),
        ], wrap='clip') for n in doc]
        focus_map = {
            None: 'focus',
            'faint': 'focus',
        }
        items = [urwid.AttrMap(w, None, focus_map) for w in items]
        schema_walker = urwid.SimpleListWalker(items)
        schema_listbox = urwid.ListBox(schema_walker)
        #doc_textbox = urwid.Edit("", multiline=True, allow_tab=True)
        self.columns.widget_list.append(schema_listbox)
            #urwid.Filler(doc_textbox, valign='top'))
        #text = json.dumps(doc, indent=4, default=encoder)
        #doc_textbox.set_edit_text(text)

    def display_list(self, values):
        list_walker = urwid.PollingListWalker([
            urwid.AttrMap(w, None, 'focus')
            for w in [
                SelectableText(json.dumps(v, default=encoder), wrap='clip')
                for v in values]])
        list_listbox = urwid.ListBox(list_walker)
        self.columns.widget_list.append(list_listbox)

    def save_document(self):
        textbox = self.columns.get_focus()
        text = textbox.get_edit_text()
        doc = json.loads(text, object_hook=object_hook)
        self.selected_collection.save(doc)
        self.display_document(doc['_id'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('database', nargs='?')
    parser.add_argument('--host', default='localhost',
                        help='server to connect to')
    parser.add_argument('--port', type=int, default=27017,
                        help='port to connect to')
    args = parser.parse_args()

    conn = pymongo.Connection(args.host, args.port)
    try:
        CollectionBrowser(conn, args.database).main()
    except KeyboardInterrupt:
        pass
