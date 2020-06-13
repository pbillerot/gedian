#!/usr/bin/python3
# -*- coding:Utf-8 -*-
"""
    Editeur des fichiers du système Debian
"""
import os
import argparse
import json
import subprocess, shlex
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GtkSource', '3.0')
gi.require_version('Vte', '2.91')
from gi.repository import Gtk, Gdk, GObject, GLib, Vte, GtkSource, GdkPixbuf

APPLICATION_NAME = "GEDIAN"
GLib.set_application_name(APPLICATION_NAME)
GLib.set_prgname(APPLICATION_NAME)

class Gedian(Gtk.Window):
    """ Fenêtre Editeur """
    GEDIAN_NAME = "gedian.list"
    is_modified = False

    def __init__(self, title="GEDIAN", gedian_directory=""):
        Gtk.Window.__init__(self, title=title)

        # CONFIG
        if gedian_directory == "":
            self.gedian_directory = os.path.expanduser("~/.local/share/gedian")
        else:
            self.gedian_directory = os.path.expanduser(gedian_directory)
        if not os.path.exists(self.gedian_directory):
            os.makedirs(self.gedian_directory)
        # os.chdir(self.gedian_directory)
        self.gedian_file = self.gedian_directory + "/" + Gedian.GEDIAN_NAME
        self.current_file = ""

        # WINDOW
        self.activate_focus()
        self.set_border_width(6)
        self.set_default_size(1024, 800)

        # CLIPBOARD
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)

        # KEYBOARD SHORTCUTS
        accel = Gtk.AccelGroup()
        accel.connect(Gdk.keyval_from_name('E'), Gdk.ModifierType.CONTROL_MASK, 0, self.on_keyboard_accel_pressed)
        accel.connect(Gdk.keyval_from_name('S'), Gdk.ModifierType.CONTROL_MASK, 0, self.on_keyboard_accel_pressed)
        self.add_accel_group(accel)
        
        # HEADBAR
        hb = Gtk.HeaderBar()
        hb.set_show_close_button(True)
        hb.props.title = title
        button_menu = Gtk.Button()
        image = Gtk.Image.new_from_icon_name("open-menu-symbolic", Gtk.IconSize.BUTTON)
        button_menu.connect("clicked", self.on_button_menu_clicked)
        button_menu.add(image)
        self.popover = Gtk.Popover()
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        help = Gtk.Label()
        help.set_markup('<a href="https://github.com/pbillerot/gedian">Aide</a>')
        vbox.pack_start(help, False, True, 10)
        button_about = Gtk.Button()
        button_about.set_label("A propos...")
        button_about.connect("clicked", self.on_button_about_clicked)
        vbox.pack_start(button_about, False, True, 10)
        self.popover.add(vbox)
        self.popover.set_position(Gtk.PositionType.BOTTOM)
        hb.pack_end(button_menu)
        self.set_titlebar(hb)

        # PANE
        # PANE_LEFT PANE_RIGHT
        pane = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        self.add(pane)

        pane_left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        pane_left.set_border_width(3)
        pane.add1(pane_left)

        pane_right = Gtk.Paned.new(Gtk.Orientation.VERTICAL)
        pane.add2(pane_right)

        # PANE_LEFT
        # BUTTON_LIST LISTBOX
        button_list = Gtk.Button.new_with_label(Gedian.GEDIAN_NAME)
        button_list.connect("clicked", self.on_button_list_clicked)
        pane_left.pack_start(button_list, False, False, 3)

        self.listbox = self.create_listbox()
        pane_left.pack_start(self.listbox, True, True, 3)

        # PANE_RIGHT
        # PANE_TOP PANE_BOTTOM
        frame_editor = Gtk.Frame()
        frame_editor.set_border_width(3)
        pane_right.add1(frame_editor)
        vbox_top = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        frame_editor.add(vbox_top)

        frame_terminal = Gtk.Frame()
        frame_terminal.set_border_width(3)
        pane_right.add2(frame_terminal)
        pane_right.set_position(300)
        vbox_bottom = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        frame_terminal.add(vbox_bottom)

        # PANE_TOP
        # TOOLBAR_EDIT EDITOR
        
        # TOOLBAR_EDIT
        self.toolbar_edit = Gtk.HBox()
        vbox_top.pack_start(self.toolbar_edit, False, True, 3)
        
        self.label_file = Gtk.Label()       
        self.toolbar_edit.pack_start(self.label_file, True, True, 3)

        self.check_crlf = Gtk.CheckButton.new_with_label("Retour à la ligne")
        self.check_crlf.connect("toggled", self.on_check_crlf_toggled)
        self.check_crlf.set_sensitive(False)
        self.toolbar_edit.pack_start(self.check_crlf, False, True, 3)

        self.button_save = Gtk.Button.new_with_label("Enregistrer")
        self.button_save.set_sensitive(False)
        self.button_save.connect("clicked", self.on_button_save_clicked)
        self.toolbar_edit.pack_end(self.button_save, False, False, 3)

        # EDITOR voir create_editor()
        self.scrolledwindow = Gtk.ScrolledWindow()
        vbox_top.pack_end(self.scrolledwindow, True, True, 0)

        # PANE_BOTTOM
        # TOOLBAR_TERMINAL TERMINAL

        # TOOLBAR_TERMINAL
        self.toolbar_terminal = Gtk.HBox()
        vbox_bottom.pack_start(self.toolbar_terminal, False, True, 3)

        self.button_paste = Gtk.Button()
        image = Gtk.Image.new_from_icon_name("go-down-symbolic", Gtk.IconSize.BUTTON)
        self.button_paste.add(image)
        self.button_paste.set_tooltip_text("Coller la ligne de l'éditeur dans le terminal")
        self.button_paste.connect("clicked", self.on_button_paste_clicked)
        self.toolbar_terminal.pack_start(self.button_paste, False, False, 0)

        self.button_exec = Gtk.Button()
        image = Gtk.Image.new_from_icon_name("media-playback-start-symbolic", Gtk.IconSize.BUTTON)
        self.button_exec.add(image)
        self.button_exec.set_tooltip_text("Valider la ligne de commande du terminal")
        self.button_exec.connect("clicked", self.on_button_exec_clicked)
        self.toolbar_terminal.pack_start(self.button_exec, False, False, 0)

        self.button_clear = Gtk.Button()
        image = Gtk.Image.new_from_icon_name("edit-clear-all-symbolic", Gtk.IconSize.BUTTON)
        self.button_clear.add(image)
        self.button_clear.set_tooltip_text("Nettoyer la fenêtre du terminal")
        self.button_clear.connect("clicked", self.on_button_clear_clicked)
        self.toolbar_terminal.pack_start(self.button_clear, False, False, 0)

        # TERMINAL
        # https://lazka.github.io/pgi-docs/Vte-2.91/classes/Terminal.html
        self.terminal = self.create_terminal()
        vbox_bottom.pack_start(self.terminal, True, True, 0)

    # GESTION LISTBOX
    def create_listbox(self):
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.connect("row-activated", self.on_row_selected)
        self.load_list() # chargement de la liste
        return self.listbox

    def load_list(self):
        for children in self.listbox.get_children():
            Gtk.Widget.destroy(children)
        self.list_files = []
        if os.path.exists(self.gedian_file):
            with open(self.gedian_file) as f:
                for line in f.readlines():
                    hbox = Gtk.HBox()
                    slabel = line.replace("\n", "")
                    label = Gtk.Label(label=slabel, xalign=0)
                    hbox.pack_start(label, True, True, 0)
                    self.listbox.add(hbox)
                    self.list_files.append(slabel)
            self.listbox.show_all()
        else:
            pass

    def on_button_list_clicked(self, widget):
        """ Chargement de textview avec la liste des fichiers """
        if self.confirm_if_modified() :
            self.current_file = self.gedian_file
            self.load_file_current()
            self.refresh_list_selection()

    def on_row_selected(self, listbox, row):
        """ une ligne de la liste est sélectionné """
        if self.confirm_if_modified() :
            path_file = self.list_files[row.get_index()]
            if path_file.find("/") == -1:
                path_file = self.gedian_directory + "/" + path_file
            path_absolute = os.path.expanduser(path_file)
            self.current_file = path_absolute 
            self.load_file_current()
        else:
            self.refresh_list_selection()

    def refresh_list_selection(self):
        """ On remet la sélection sur la ligne du fichier ouvert """
        self.listbox.unselect_all()
        irow = 0
        for path_file in self.list_files:
            if path_file.find("/") == -1:
                path_file = self.gedian_directory + "/" + path_file
            path_absolute = os.path.expanduser(path_file)
            if path_absolute == self.current_file:
                self.listbox.select_row(self.listbox.get_row_at_index(irow))
            irow += 1


    def confirm_if_modified(self):
        bret = True
        if self.is_modified :
            dialog = Gtk.MessageDialog(parent=self,
                modal=True, destroy_with_parent=True,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.YES_NO,
                text="Le fichier courant n'a pas été enregistré")
            dialog.format_secondary_text(
                "Confirmer par [Oui] pour abandonner les modifications"
                )
            response = dialog.run()
            if response == Gtk.ResponseType.CANCEL:
                bret = False
            dialog.destroy()
        return bret

    # GESTION EDITEUR
    # https://lazka.github.io/pgi-docs/GtkSource-3.0/index.html
    # https://lazka.github.io/pgi-docs/GtkSource-3.0/classes/View.html
    # https://lazka.github.io/pgi-docs/GtkSource-3.0/classes/Buffer.html   
    # http://mcclinews.free.fr/python/pygtktutfr/sec-TextBuffers.html    
    # https://sourceforge.net/p/gtksourceview/wiki/markdown_syntax/  
    def create_editor(self, content):
        for children in self.scrolledwindow.get_children():
            Gtk.Widget.destroy(children)

        lang_manager = GtkSource.LanguageManager()
        language = lang_manager.guess_language(self.current_file, None)
        
        self.source_buffer = GtkSource.Buffer()
        self.source_buffer.set_language(language)
        self.source_buffer.set_text(content)
        self.source_buffer.set_highlight_syntax(True)
        self.source_buffer.connect("changed", self.on_textbuffer_changed)
        # self.source_buffer.set_highlight_matching_brackets(True

        self.source_editor = GtkSource.View(
            name='text_editor',
            buffer=self.source_buffer,
            monospace=True,
            insert_spaces_instead_of_tabs=True,
            tab_width=4,
            highlight_current_line=True,
            auto_indent=True,
            wrap_mode=Gtk.WrapMode.NONE
        )
        # self.source_editor.set_editable(False)
        self.scrolledwindow.add(self.source_editor)
        self.show_all()

    def get_editor_current_line(self):
        """ Obtenir la ligne courante """
        iter = self.source_buffer.get_iter_at_mark(self.source_buffer.get_insert())
        end = iter.copy()
        end.forward_line()
        start = end.copy()
        start.backward_line()
        sline = self.source_buffer.get_text(start, end, False)
        # passage ligne suivante
        iter.forward_lines(1)
        self.source_buffer.place_cursor(iter)
        return sline.replace("\n", "")

    def on_textbuffer_changed(self, widget):
        """ Le texte a été modifié """
        self.is_modified = True
        self.button_save.set_sensitive(True)
        self.label_file.set_markup("<b>"+ self.current_file + " *" + "</b>")

    def paste_current_line(self):
        """ on colle la ligne courante dans le terminal """
        # Sélection de la ligne courante, copie dans le clipboard et coller dans le terminal
        sline = self.get_editor_current_line()
        self.clipboard.set_text(sline, -1)
        self.terminal.paste_clipboard()

    # GESTION DU TERMINAL
    # https://lazka.github.io/pgi-docs/Vte-2.91/classes/Terminal.html
    def create_terminal(self):
        self.terminal = Vte.Terminal()
        pty = Vte.Pty.new_sync(Vte.PtyFlags.DEFAULT)
        self.terminal.set_pty(pty)
        pty.spawn_async(
            os.environ['HOME'],
            ["/bin/bash"],
            None,
            GLib.SpawnFlags.DO_NOT_REAP_CHILD,
            None,
            None,
            -1,
            None,
            self.on_vte_ready
            )
        self.terminal.connect("key_press_event", self.on_terminal_copy_or_paste)
        return self.terminal

    def on_vte_ready(self, pty, task):
        """ Démarrage du terminal vte """
        pass

    def on_terminal_copy_or_paste(self, widget, event):
        """ TERMINAL
        Traitement du Ctrl+Shift+C pour copier dans le clipboard
        ou Ctrl+Shift+V pour le coller
        """
        control_key = Gdk.ModifierType.CONTROL_MASK
        shift_key = Gdk.ModifierType.SHIFT_MASK
        if event.type == Gdk.EventType.KEY_PRESS:
            if event.state & shift_key and event.state & control_key: #both shift  and control
                if event.keyval == 67: # that's the C key
                    self.terminal.copy_clipboard_format(Vte.Format.TEXT)
                elif event.keyval == 86: # and that's the V key
                    self.terminal.paste_clipboard()
                return True

    # GESTION DES EVENEMENTS 
    def on_keyboard_accel_pressed(self, *args):
        """ Ctrl+key """
        if args[2] == 101 : # ctrl+E
            self.exec_current_line()
        if args[2] == 115 : # ctrl+S
            if self.is_modified : self.button_save.clicked()

    def on_button_menu_clicked(self, button):
        self.popover.set_relative_to(button)
        self.popover.show_all()
        self.popover.popup()

    def on_popover_menu_clicked(self, button, button_name):
        print("popover", button_name)

    def on_button_save_clicked(self, widget):
        """ Sauvegarde du fichier """
        self.save_file_current()
    
    def on_button_paste_clicked(self, widget):
        """ On colle la ligne courante de l'éditeur dans le terminal"""
        self.paste_current_line()

    def on_button_exec_clicked(self, widget):
        """ Exécution de la ligne courante """
        # Collage du \n copie dans le clipboard
        self.clipboard.set_text("\n", -1)
        self.terminal.paste_clipboard()

    def on_button_clear_clicked(self, widget):
        """ Noeetoyage du terminal """
        self.clipboard.set_text("clear\n", -1)
        self.terminal.paste_clipboard()
    
    def on_check_crlf_toggled(self, button):
        """ gestion retour à la ligne """
        if button.get_active() :
            self.source_editor.set_wrap_mode(Gtk.WrapMode.WORD)
        else:
            self.source_editor.set_wrap_mode(Gtk.WrapMode.NONE)
    
    # GESTION DES FICHIERS
    def load_file_current(self):
        data = ""
        if os.path.exists(self.current_file):
            with open(self.current_file) as f:
                data = f.read()

        self.create_editor(data)

        self.label_file.set_markup("<b>"+ self.current_file + "</b>")
        self.button_save.set_sensitive(False)
        self.check_crlf.set_sensitive(True)
        self.button_exec.set_sensitive(True)
        self.is_modified = False

    def save_file_current(self):
        iStart, iEnd = self.source_buffer.get_bounds()
        data = self.source_buffer.get_text(iStart, iEnd, True)

        pathfile = self.current_file
        # BACKUP du fichier.bak dans le répertoire gedian
        if self.current_file.find("local/share/debian") == -1:
            # création de la même arborescence sous gedian
            pathfile = os.path.abspath(".") + self.current_file
            directory = os.path.dirname(pathfile)
            if not os.path.exists(directory):
                os.makedirs(directory)
        cmd = "cp '{}' '{}.bak'".format(self.current_file, pathfile)
        subprocess.Popen(shlex.split(cmd))

        # RECOPIE du fichier modifié dans gedian
        if self.current_file.find("local/share/debian") == -1:
            with open(pathfile, "w") as f:           
                f.write(data) 

        # CTRL DROIT d'écriture
        if os.access(self.current_file, os.W_OK):
            # ENREGISTREMENT
            with open(self.current_file, "w") as f:           
                f.write(data) 
        else:            
            # ENREGISTREMENT dans le répertoire système en sudo
            cmd = "pkexec cp '{}' '{}'".format(pathfile, self.current_file)
            subprocess.Popen(shlex.split(cmd))

        if self.current_file == self.gedian_file:
            # chargement de la liste
            self.load_list()
        self.button_save.set_sensitive(False)
        self.is_modified = False
        self.label_file.set_markup("<b>"+ self.current_file + "</b>")

    def on_button_about_clicked(self, widget):
        """
        La fenêtre About...
        """
        about = Gtk.AboutDialog()
        about.set_transient_for(self)
        about.set_title(APPLICATION_NAME)
        about.set_program_name(APPLICATION_NAME)
        about.set_version("20.6.13")
        about.set_copyright("pbillerot@github.com")
        about.set_comments("Editeur des fichiers d'un système DEBIAN")
        about.set_website("https://github.com/pbillerot/gedian")
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(get_resource_path("./gedian.svg"))
        about.set_logo(pixbuf)
        with open(get_resource_path("LICENSE"), 'r') as file:
            about.set_license(file.read())
        about.connect("response", lambda d, r: d.destroy())
        about.show()

    def get_resource_path(self, rel_path):
        dir_of_py_file = os.path.dirname(__file__)
        rel_path_to_resource = os.path.join(dir_of_py_file, rel_path)
        abs_path_to_resource = os.path.abspath(rel_path_to_resource)
        return os.path.expanduser(abs_path_to_resource)

def get_resource_path(rel_path):
    dir_of_py_file = os.path.dirname(__file__)
    rel_path_to_resource = os.path.join(dir_of_py_file, rel_path)
    abs_path_to_resource = os.path.abspath(rel_path_to_resource)
    return os.path.expanduser(abs_path_to_resource)

def replace_in_file(file_path_in , file_path_out, dico):
    fin = open(file_path_in, "rt")
    fout = open(file_path_out, "wt")
    for line in fin:
        for key in dico:
            fout.write(line.replace(key, dico[key]))
    fin.close()
    fout.close()

# Point d'entrée
parser = argparse.ArgumentParser()
parser.add_argument('-install', action='store_true', default=False, help="Installation de gedian.desktop dans Gnome")
args = parser.parse_args()
if args.install:
    # Valorisation des variables dans gedian.desktop et copie dans gnome
    dico = {
        "{path_gedian}": get_resource_path("")
    }
    replace_in_file(
        get_resource_path("gedian.desktop"),
        os.path.expanduser("~/.local/share/applications/gedian.desktop"),
        dico)
    print("GEDIAN installé")
else:
    win = Gedian()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

""" LAYOUT
headbar
pane_left  pane_right

pane_left
button gedian.list
listbox gedian.list

pane_right
pane_top  pane_bottom

pane_top
toolbar_edit
editor

pane_bottom
toolbar_terminal
terminal

"""