from gi.repository import Gtk
from gi.repository import GdkPixbuf
from gi.repository import GLib

class MessageControl(object):
    """
    An abstract base widget that can embed in the Gtk.Notebook of a
    MessageWindow
    """

    def __init__(self, type_id, parent_win, widget_name, contact):
        # dict { cb id : widget}
        # keep all registered callbacks of widgets, created by self.xml
        self.handlers = {}
        self.type_id = type_id
        self.parent_win = parent_win
        self.widget_name = widget_name
        self.contact = contact
        self.hide_chat_buttons = False

        self.session = None

        self.xml = Gtk.Builder()
        self.xml.add_from_file('glade/' + widget_name + '.glade')

        self.widget = self.xml.get_object(widget_name)

        #gajim.ged.register_event_handler('message-outgoing', ged.OUT_GUI1,
        #    self._nec_message_outgoing)

    def get_alias(self):
         return self.contact