import mtalkconn

import roster_window
from threading import Thread

from gi.repository import Gtk
from gi.repository import GdkPixbuf
from gi.repository import GLib

from chat_control import ChatControl

import variables

class Interface:

    def __init__(self):
        variables.interface = self
        variables.thread_interface = ThreadInterface
        # This is the manager and factory of message windows set by the module
        self.msg_win_mgr = None

    def run(self):
        self.roster = roster_window.RosterWindow()



        #fill the roster contacts...
        #self.roster._before_fill()
        #for account in gajim.connections:
        #    gajim.connections[account].load_roster_from_db()
        #self.roster._after_fill()

        #connect here possibly by using glib timeout_add

        #connect to idle queue of gcm connector?

        import config
        import dialogs
        if not config.existsConfigOption('gcmandroidId'):
            dialogs.GenerateGCMWindow()
        else:
            mtalkconn.start_gcm(self)


    def on_open_chat_window(self, widget, contact, resource=None, session=None):

        ctrl = None

        if session:
            ctrl = session.control
        if not ctrl:
            win = self.msg_win_mgr.get_window()

            if win:
                ctrl = win.get_control(contact)

        if not ctrl:
            ctrl = self.new_chat(contact,  session=session)

        win = ctrl.parent_win

        win.set_active_tab(ctrl)

        #if gajim.connections[account].is_zeroconf and \
        #gajim.connections[account].status in ('offline', 'invisible'):
        #    ctrl = win.get_control(fjid, account)
        #    if ctrl:
        #        ctrl.got_disconnected()

    def new_chat(self, alias, session=None):
        # Get target window, create a control, and associate it with the window

        mw = self.msg_win_mgr.get_window()
        if not mw:
            mw = self.msg_win_mgr.create_window()

        chat_control = ChatControl(mw, alias)

        mw.new_tab(chat_control)

        #chat_control.read_queue()

        return chat_control

    def received_message(self, data):
        alias = data['alias']
        message = data['message']
        chat_control = self.msg_win_mgr.get_control(alias)
        if not chat_control:
            mw = self.msg_win_mgr.create_window()
            chat_control = ChatControl(mw, alias)
            mw.new_tab(chat_control)

        chat_control.print_conversation(message)

class ThreadInterface:
    def __init__(self, func, func_args=(), callback=None, callback_args=()):
        """
        Call a function in a thread
        """
        def thread_function(func, func_args, callback, callback_args):
            output = func(*func_args)
            if callback:
                GLib.idle_add(callback, output, *callback_args)

        Thread(target=thread_function, args=(func, func_args, callback,
                callback_args)).start()