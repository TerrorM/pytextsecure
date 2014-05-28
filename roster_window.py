from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import Pango
from gi.repository import GObject
from gi.repository import GLib

from message_window import MessageWindowMgr

import variables

import dialogs


#(icon, name, type, jid, account, editable, second pixbuf)
(
    C_NAME, # cellrenderer text that holds contact nickame
    C_TYPE, # account, group or contact?
    C_PHONE, # the jid of the row
    C_PUB_KEY, # the jid of the row
) = range(4)


class RosterWindow():

    def __init__(self):

        self.columns = [str]

        self.xml = Gtk.Builder()
        self.xml.add_from_file('glade/roster_window.glade')
        self.xml.connect_signals(self)

        self.window = self.xml.get_object('roster_window')
        self.paned = self.xml.get_object('roster_paned')

        variables.interface.msg_win_mgr = MessageWindowMgr(self.window, self.paned)
        variables.interface.msg_win_mgr.connect('window-delete',
            self.on_message_window_delete)


        self.tree = self.xml.get_object('roster_treeview')


        # columns
        # do not show gtk arrows workaround
        col = Gtk.TreeViewColumn("Contacts")
        title = Gtk.CellRendererText()

        col.pack_start(title, False)
        col.add_attribute(title, "text", 0)
        self.tree.append_column(col)

        self.tree.set_expander_column(col)
        # list of renderers with attributes / properties in the form:
        # (name, renderer_object, expand?, attribute_name, attribute_value,
        # cell_data_func, func_arg)
        self.renderers_list = []
        self.renderers_propertys ={}

        self.setup_and_draw_roster()

        self.window.show_all()

    def setup_and_draw_roster(self):
        """
        Create new empty model and draw roster
        """
        self.modelfilter = None
        self.model = Gtk.ListStore(*self.columns)

        #self.model.set_sort_func(1, self._compareIters)
        #self.model.set_sort_column_id(1, Gtk.SortType.ASCENDING)
        #self.modelfilter = self.model.filter_new()
        #self.modelfilter.set_visible_func(self._visible_func)
        #self.modelfilter.connect('row-has-child-toggled',
        #        self.on_modelfilter_row_has_child_toggled)
        self.tree.set_model(self.model)

        #self._iters = {}
        # for merged mode
        #self._iters['MERGED'] = {'account': None, 'groups': {}}
        #for acct in gajim.contacts.get_accounts():
        #    self._iters[acct] = {'account': None, 'groups': {}, 'contacts': {}}

        #for acct in gajim.contacts.get_accounts():
        #    self.add_account(acct)
        #    self.add_account_contacts(acct, improve_speed=True,
        #        draw_contacts=False)

        self.add_contacts()

        # Recalculate column width for ellipsizing
        self.tree.columns_autosize()

    def _compareIters(self):
        pass

    def _visible_func(self):
        pass

    def add_contacts(self):
        #store = self.xml.get_object('liststore1')

        import keyutils
        recipients = keyutils.RecipientUtil().getAllRecipients()
        for recipient in recipients:
            if recipient.alias == None:
                self.add_contact(recipient.phoneNumber)
            else:
                self.add_contact(recipient.alias)

        #treeview = self.builder.get_object('treeview2')

    def add_contact(self, alias):
        self.model.append([alias])

    def on_quit_request(self, widget=None):
        self.quit_gtkgui_interface()

    def quit_gtkgui_interface(self):
        """
        When we quit the gtk interface - exit gtk
        """
        #self.prepare_quit()
        Gtk.main_quit()

    def on_roster_window_delete_event(self, widget, event):
        """
        Main window X button was clicked
        """
        self.on_quit_request()


    def on_message_window_delete(self, win_mgr, msg_win):
        pass


    def on_roster_treeview_row_activated(self, widget, path, col=0):
        """
        When an iter is double clicked: open the first event window
        """
        self.on_row_activated(widget, path)

    def on_row_activated(self, widget, path):
        model = self.model
        contact = model[path][0]

        variables.interface.on_open_chat_window(None, contact, session=None)

    def about_activate(self, action):
        about_dlg = self.xml.get_object('aboutdialog1')
        about_dlg.run()
        about_dlg.hide()

    def on_create_new_account(self, widget):
        #Check if we have already setup GCM
        import config
        if not config.existsConfigOption('gcmandroidId'):
            dialogs.GenerateGCMWindow()
        else:
            dialogs.AccountCreationWizardWindow()

    def on_add_new_contact(self, widget):
        dialogs.AddNewContactWindow()