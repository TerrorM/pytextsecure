from gi.repository import Gtk, Gdk, GObject
from gi.overrides import keysyms

import serverapi
import threading

class HigDialog(Gtk.MessageDialog):
    def __init__(self, parent, type_, buttons, pritext, sectext,
                 on_response_ok=None, on_response_cancel=None, on_response_yes=None,
                 on_response_no=None):
        Gtk.MessageDialog.__init__(self, parent,
                                   Gtk.DialogFlags.DESTROY_WITH_PARENT | Gtk.DialogFlags.MODAL,
                                   type_, buttons, message_format=pritext)

        self.format_secondary_markup(sectext)

        buttons = self.action_area.get_children()
        possible_responses = {'_OK': on_response_ok,
                              '_CANCEL': on_response_cancel, '_YES': on_response_yes,
                              '_NO': on_response_no}
        for b in buttons:
            for response in possible_responses:
                if b.get_label() == response:
                    if not possible_responses[response]:
                        b.connect('clicked', self.just_destroy)
                    elif isinstance(possible_responses[response], tuple):
                        if len(possible_responses[response]) == 1:
                            b.connect('clicked', possible_responses[response][0])
                        else:
                            b.connect('clicked', *possible_responses[response])
                    else:
                        b.connect('clicked', possible_responses[response])
                    break

    def just_destroy(self, widget):
        self.destroy()

    def popup(self):
        #show dialog
        vb = self.get_children()[0].get_children()[0]  # Give focus to top vbox
        #vb.set_flags(Gtk.CAN_FOCUS)
        vb.grab_focus()
        self.show_all()


class InformationDialog(HigDialog):
    def __init__(self, pritext, sectext=''):
        #HIG compliant info dialog.
        HigDialog.__init__(self, None,
                           Gtk.MessageType.INFO, Gtk.ButtonsType.OK, pritext, sectext)
        self.popup()


class ErrorDialog(HigDialog):
    def __init__(self, pritext, sectext=''):
        #HIG compliant error dialog.
        HigDialog.__init__(self, None,
                           Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, pritext, sectext)
        self.popup()
        #d = Gtk.MessageDialog(self, Gtk.DialogFlags.MODAL, Gtk.MessageType.WARNING, Gtk.ButtonsType.OK)
        #d.set_markup('blah')
        #d.run()
        #d.destroy()


class GenerateGCMWindow(object):

    def __init__(self):

        #if self.account:
        #    location = gajim.interface.instances[self.account]
        #else:
        #    location = gajim.interface.instances
        #if 'add_contact' in location:
        #    location['add_contact'].window.present()
        # An instance is already opened
        #return
        #location['add_contact'] = self


        self.builder = Gtk.Builder()
        self.builder.add_from_file('glade/generate_gcm_token_window.glade')
        self.builder.connect_signals(self)

        self.window = self.builder.get_object('generate_gcm_token_window')

        # Generic widgets
        self.add_button = self.builder.get_object('generate_button')
        self.google_email_entry = self.builder.get_object('google_email_entry')
        self.password_entry = self.builder.get_object('password_entry')
        self.cancel_button = self.builder.get_object('cancel_button')

        #

        self.window.show_all()

    def on_add_new_contact_window_destroy(self, widget):
        #if self.account:
        #    location = gajim.interface.instances[self.account]
        #else:
        #    location = gajim.interface.instances
        #del location['add_contact']
        pass

    def on_generate_gcm_token_window_key_press_event(self, widget, event):
        if event.keyval == keysyms.Escape:  # ESCAPE
            self.window.destroy()

    def on_cancel_button_clicked(self, widget):
        #When Cancel button is clicked
        self.window.destroy()

    def on_add_button_clicked(self, widget):
        #When Subscribe button is clicked

        google_email = self.google_email_entry.get_text()
        password = self.password_entry.get_text()

        from gcm import googleplayapi

        try:
            import mtalkconn
            mtalkconn.configGCM(google_email, password)

        except googleplayapi.ServerError as e:
            ErrorDialog('Error', str(e))
            return

        except googleplayapi.LoginError as e:
            ErrorDialog('Error', str(e))
            return

        except Exception as e:
            ErrorDialog('Error', str(e))
            return


        InformationDialog('Success', 'Successfully Generated GCM Authentication Token!')
        self.window.destroy()
        AccountCreationWizardWindow()

class AddNewContactWindow(object):
    #Class for AddNewContactWindow

    def __init__(self, account=None, jid=None, user_nick=None, group=None):

        #if self.account:
        #    location = gajim.interface.instances[self.account]
        #else:
        #    location = gajim.interface.instances
        #if 'add_contact' in location:
        #    location['add_contact'].window.present()
        # An instance is already opened
        #return
        #location['add_contact'] = self


        self.builder = Gtk.Builder()
        self.builder.add_from_file('glade/add_new_contact_window.glade')
        self.builder.connect_signals(self)

        self.window = self.builder.get_object('add_new_contact_window')

        # Generic widgets
        self.phone_entry = self.builder.get_object('phone_entry')
        self.alias_entry = self.builder.get_object('alias_entry')
        self.cancel_button = self.builder.get_object('cancel_button')
        self.back_button = self.builder.get_object('back_button')
        self.add_button = self.builder.get_object('add_button')

        self.window.show_all()

    def on_add_new_contact_window_destroy(self, widget):
        #if self.account:
        #    location = gajim.interface.instances[self.account]
        #else:
        #    location = gajim.interface.instances
        #del location['add_contact']
        pass

    def on_add_new_contact_window_key_press_event(self, widget, event):
        if event.keyval == keysyms.Escape:  # ESCAPE
            self.window.destroy()

    def on_cancel_button_clicked(self, widget):
        #When Cancel button is clicked
        self.window.destroy()

    def on_add_button_clicked(self, widget):
        #When Subscribe button is clicked

        phone_entry = self.phone_entry.get_text()
        alias = self.alias_entry.get_text()

        try:
            preKeyList = serverapi.getRecipientsPreKeyList(phone_entry)

        except serverapi.ServerError as e:
            ErrorDialog('Error', str(e))
            return

        phoneNumber = phone_entry
        identityKey = preKeyList.keys[0].identityKey.publicKey
        alias = alias

        import keyutils
        keyutils.RecipientUtil().saveRecipient(phoneNumber, identityKey, alias)

        self.window.destroy()


class AccountCreationWizardWindow(object):
    def __init__(self):

        self.builder = Gtk.Builder()
        self.builder.add_from_file('glade/account_creation_wizard_window.glade')
        self.builder.connect_signals(self)

        self.window = self.builder.get_object('account_creation_wizard_window')

        # Generic widgets
        self.notebook = self.builder.get_object('notebook')
        self.cancel_button = self.builder.get_object('cancel_button')
        self.back_button = self.builder.get_object('back_button')
        self.forward_button = self.builder.get_object('forward_button')
        self.finish_button = self.builder.get_object('finish_button')
        self.finish_label = self.builder.get_object('finish_label')
        self.progressbar = self.builder.get_object('progressbar')
        self.progressbar_label = self.builder.get_object('progressbar_label')

        #self.window.connect('destroy', lambda x: Gtk.main_quit())
        self.window.show_all()

    def on_cancel_button_clicked(self, widget):
        self.window.destroy()

    def on_back_button_clicked(self, widget):
        cur_page = self.notebook.get_current_page()
        print(cur_page)
        if cur_page in (1, 2):
            self.notebook.set_current_page(0)
            self.back_button.set_sensitive(False)
        elif cur_page == 3:
            if self.phone:
                self.notebook.set_current_page(1)  # Go to phone page
            else:
                self.notebook.set_current_page(2)  # Go to email page
        elif cur_page == 5:  # finish page
            self.forward_button.show()
            if self.attempt_token:
                self.builder.get_object('secret_token_entry').set_text("")
                self.notebook.set_current_page(3)
            elif self.phone:
                self.notebook.set_current_page(1)  # Go to phone page
            else:
                self.notebook.set_current_page(2)  # Go to email page

    def register_phone_number(self, phone_number):

        try:
            serverapi.requestVerificationCode(phone_number)

            Gdk.threads_enter()
            self.phone_number = phone_number

            if self.update_progressbar_timeout_id is not None:
                GObject.source_remove(self.update_progressbar_timeout_id)

            self.back_button.show()
            self.forward_button.show()
            self.notebook.set_current_page(3)
            Gdk.threads_leave()

        except serverapi.ServerError as e:
            self.server_error(e.message)

            # show secret token page
            # instead of using global locks we could emit signals?

    def check_token(self, token):
        self.attempt_token = True

        try:
            serverapi.confirmVerificationCode(self.phone_number, token)
            #success generate prekeys

            Gdk.threads_enter()
            progress_text = '<b>%s</b>\n\n%s' % (
                'Verification code confirmed',
                'Please wait uploadings public keys to server... ')
            self.progressbar_label.set_markup(progress_text)
            Gdk.threads_leave()

            serverapi.registerGCMid()
            serverapi.registerPreKeys()

            Gdk.threads_enter()
            if self.update_progressbar_timeout_id is not None:
                GObject.source_remove(self.update_progressbar_timeout_id)

            self.cancel_button.hide()
            self.back_button.hide()
            self.forward_button.hide()
            finish_text = '<big><b>%s</b></big>\n\n%s' % (
                'Account has been added successfully',
                'You can set advanced account options by pressing the '
                'Advanced button, or later by choosing the Accounts menuitem '
                'under the Edit menu from the main window.')
            self.finish_label.set_markup(finish_text)
            self.finish_button.show()
            self.finish_button.set_property('has-default', True)
            img = self.builder.get_object('finish_image')
            img.set_from_stock(Gtk.STOCK_APPLY, Gtk.IconSize.DIALOG)
            self.notebook.set_current_page(5)  # show finish page
            Gdk.threads_leave()

        except serverapi.ServerError as e:
            self.server_error(e.message)

    def on_forward_button_clicked(self, widget):
        cur_page = self.notebook.get_current_page()
        self.attempt_token = 0

        if cur_page == 0:
            widget = self.builder.get_object('register_phone_radiobutton')
            if widget.get_active():
                self.phone = True
                self.notebook.set_current_page(1)
            else:
                self.phone = False
                self.notebook.set_current_page(2)
            self.back_button.set_sensitive(True)
            return

        elif cur_page == 1:
            # We are creating a phone number account
            phone_number = self.builder.get_object('phone_entry').get_text()

            threading.Thread(target=self.register_phone_number,
                             args=( phone_number, ),
            ).start()

            self.notebook.set_current_page(4)  # show creating page
            self.back_button.hide()
            self.forward_button.hide()
            self.update_progressbar_timeout_id = GObject.timeout_add(100,
                                                                     self.update_progressbar)

        elif cur_page == 2:
            # We are creating an email account
            email = self.builder.get_object('email_entry').get_text()
            threading.Thread(target=self.register_phone_number,
                             args=( email, ),
            ).start()

            self.notebook.set_current_page(4)  # show creating page
            self.back_button.hide()
            self.forward_button.hide()
            self.update_progressbar_timeout_id = GObject.timeout_add(100,
                                                                     self.update_progressbar)


            #talk to server, then when it successed go to: new_acc_connected
            #otherwise go to server_error

            #self.server_error('fucked')

            # show secret token page
            self.back_button.show()
            self.forward_button.show()
            self.notebook.set_current_page(3)

        elif cur_page == 3:
            #check SMS or Email token
            secret_token = self.builder.get_object('secret_token_entry').get_text()

            self.notebook.set_current_page(4)  # show creating page
            self.back_button.hide()
            self.forward_button.hide()
            self.update_progressbar_timeout_id = GObject.timeout_add(100,
                                                                     self.update_progressbar)

            threading.Thread(target=self.check_token,
                             args=( secret_token, ),
                             ).start()

            #self.cancel_button.show()
            #self.back_button.show()
            #self.forward_button.show()

    def update_progressbar(self):
        self.progressbar.pulse()
        return True  # loop forever

    def server_error(self, reason):
        Gdk.threads_enter()
        #Account creation failed: connection to server failed
        if self.update_progressbar_timeout_id is not None:
            GObject.source_remove(self.update_progressbar_timeout_id)

        self.forward_button.hide()
        self.back_button.show()
        self.cancel_button.show()
        img = self.builder.get_object('finish_image')
        img.set_from_stock(Gtk.STOCK_DIALOG_ERROR, Gtk.IconSize.DIALOG)
        finish_text = '<big><b>%s</b></big>\n\n%s' % (
            'An error occurred during account creation', reason)
        self.finish_label.set_markup(finish_text)
        self.notebook.set_current_page(5)  # show finish page
        Gdk.threads_leave()

    def on_finish_button_clicked(self, widget):
        self.window.destroy()

        #def on_username_entry_key_press_event(self, widget, event):
        #    # Check for pressed @ and jump to combobox if found
        #    if event.keyval == gtk.keysyms.at:
        #        combobox = self.builder.get_object('server_comboboxentry')
        #        combobox.grab_focus()
        #        combobox.child.set_position(-1)
        #        return True
