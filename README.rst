Cursed Mongo
============

A really simple curses based mongo browser, capable of simple updates.


Usage
-----

To run it type cursedmongo.py <database>.

The screen is split into 3 sections. The top section lists the collections, use
the cursor keys to move around and select a collection by pressing enter. This
will load a list of documents into the bottom left hand pane showing the value
of the documents _id field.

At the moment to switch panes you have to use the cursor keys as well and
scroll all the way to the top/bottom. Selecting a document loads it into the
bottom right pane where you can edit the JSON and save (back in one of the
other panes) by pressing 's'.

