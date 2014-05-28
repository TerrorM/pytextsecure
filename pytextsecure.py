#!/usr/bin/env python3

#GTK autocompletion...
import sys
import os

kFakegirCache = os.path.join(os.path.expanduser('~'), '.cache/fakegir')
if kFakegirCache in sys.path:
    sys.path.remove(kFakegirCache)

from gi.repository import Gtk, Gdk, GObject

from gui_interface import Interface

Gdk.threads_init()

def main():
    interface = Interface()
    interface.run()
    Gtk.main()


if __name__ == '__main__':
    main()

