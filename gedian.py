#!/usr/bin/python3
# -*- coding:Utf-8 -*-
"""
    Editeur des fichiers du système Debian
    TODO bug close onglet
"""
import os
import argparse
import json
import subprocess, shlex
from pprint import pprint
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
    notebook_pages = {}
    notebook_tabs = []
    current_file = ""
    list_files = []

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
        help = Gtk.LinkButton.new_with_label("https://github.com/pbillerot/gedian", "Aide")
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
        self.notebook = Gtk.Notebook()
        self.notebook.connect("switch-page", self.on_switch_page)
        self.notebook.set_border_width(3)
        self.notebook.set_scrollable(True)
        pane_right.add1(self.notebook)

        vbox_bottom = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        vbox_bottom.set_border_width(3)
        pane_right.add2(vbox_bottom)
        pane_right.set_position(400)

        # PANE_TOP
        # NOTEBOOK
        
        # TOOLBAR_TERMINAL TERMINAL

        # TOOLBAR_TERMINAL_-EDITOR
        self.actionbar_terminal = Gtk.ActionBar()
        vbox_bottom.pack_start(self.actionbar_terminal, False, True, 0)

        self.button_paste = Gtk.Button()
        image = Gtk.Image.new_from_icon_name("go-down-symbolic", Gtk.IconSize.BUTTON)
        self.button_paste.add(image)
        self.button_paste.set_tooltip_text("Coller la ligne de l'éditeur dans le terminal")
        self.button_paste.connect("clicked", self.on_button_paste_clicked)
        self.actionbar_terminal.pack_start(self.button_paste)

        self.button_exec = Gtk.Button()
        image = Gtk.Image.new_from_icon_name("media-playback-start-symbolic", Gtk.IconSize.BUTTON)
        self.button_exec.add(image)
        self.button_exec.set_tooltip_text("Valider la ligne de commande du terminal")
        self.button_exec.connect("clicked", self.on_button_exec_clicked)
        self.actionbar_terminal.pack_start(self.button_exec)

        self.button_clear = Gtk.Button()
        image = Gtk.Image.new_from_icon_name("edit-clear-all-symbolic", Gtk.IconSize.BUTTON)
        self.button_clear.add(image)
        self.button_clear.set_tooltip_text("Nettoyer la fenêtre du terminal")
        self.button_clear.connect("clicked", self.on_button_clear_clicked)
        self.actionbar_terminal.pack_start(self.button_clear)

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
        self.list_files.clear()    
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
        """ Chargement de l'éditeur avec gedian.list """
        self.select_file(self.gedian_file)
        self.refresh_list_selection()

    def on_row_selected(self, listbox, row):
        """ une ligne de la liste est sélectionné """
        path_file = self.list_files[row.get_index()]
        if path_file.find("/") == -1:
            path_file = self.gedian_directory + "/" + path_file
        path_absolute = os.path.expanduser(path_file)
        self.select_file(path_absolute)

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

    def confirm_if_modified(self, path_file):
        bret = True
        if self.notebook_pages[path_file]["is_modified"] :
            dialog = Gtk.MessageDialog(parent=self,
                modal=True, destroy_with_parent=True,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.YES_NO,
                text="Le fichier [" + path_file + "] n'a pas été enregistré")
            dialog.format_secondary_text(
                "Confirmer par [Oui] pour abandonner les modifications"
                )
            response = dialog.run()
            if response == Gtk.ResponseType.NO:
                bret = False
            dialog.destroy()
        return bret

    # GESTION EDITEUR
    # https://lazka.github.io/pgi-docs/GtkSource-3.0/index.html
    # https://lazka.github.io/pgi-docs/GtkSource-3.0/classes/View.html
    # https://lazka.github.io/pgi-docs/GtkSource-3.0/classes/Buffer.html   
    # http://mcclinews.free.fr/python/pygtktutfr/sec-TextBuffers.html    
    # https://sourceforge.net/p/gtksourceview/wiki/markdown_syntax/  
    def add_page_notebook(self, file_path):
        """ Ajout d'une nouvelle page au notebook """
        vbox_page = Gtk.VBox()

        # EDITEUR dans une scrolledwindow
        self.current_file = file_path
        data = ""
        if os.path.exists(file_path):
            with open(file_path) as f:
                data = f.read()

        lang_manager = GtkSource.LanguageManager()
        language = lang_manager.guess_language(file_path, None)
        
        source_buffer = GtkSource.Buffer()
        source_buffer.set_language(language)
        source_buffer.set_text(data)
        source_buffer.set_highlight_syntax(True)
        source_buffer.connect("changed", self.on_textbuffer_changed)
        # source_buffer.set_highlight_matching_brackets(True

        source_editor = GtkSource.View(
            name='text_editor',
            buffer=source_buffer,
            monospace=True,
            insert_spaces_instead_of_tabs=True,
            tab_width=4,
            highlight_current_line=True,
            auto_indent=True,
            wrap_mode=Gtk.WrapMode.NONE
        )
        # source_editor.set_editable(False)
        scrolledwindow = Gtk.ScrolledWindow()
        scrolledwindow.add(source_editor)
        vbox_page.pack_start(scrolledwindow, True, True, 0)

        # TOOLBAR
        actionbar = Gtk.ActionBar()
        button_save = Gtk.Button()
        image = Gtk.Image.new_from_icon_name("document-save-symbolic", Gtk.IconSize.SMALL_TOOLBAR)
        button_save.add(image)
        button_save.set_tooltip_text("Enregistrer")
        button_save.set_sensitive(False)
        button_save.connect("clicked", self.on_button_save_clicked)
        actionbar.pack_end(button_save)

        self.check_crlf = Gtk.CheckButton.new_with_label("Retour à la ligne")
        self.check_crlf.connect("toggled", self.on_check_crlf_toggled)
        actionbar.pack_end(self.check_crlf)
        
        vbox_page.pack_end(actionbar, False, False, 0)

        label_page = Gtk.Label()
        label_page.set_tooltip_text(self.current_file)
        label_page.show()

        image = Gtk.Image.new_from_icon_name("window-close-symbolic", Gtk.IconSize.MENU)
        image.show()

        button_close = Gtk.Button()
        button_close.add(image)
        button_close.set_relief(Gtk.ReliefStyle.NONE)
        button_close.set_tooltip_text("Fermer")
        button_close.show()
        button_close.connect("clicked", self.on_button_close_clicked, vbox_page) 

        hbox_label = Gtk.HBox()
        hbox_label.pack_start(label_page, True, True, 0)
        hbox_label.pack_end(button_close, False, False, 0)
        actionbar.show_all()

        # ipage = self.notebook.append_page(child=vbox_page, tab_label=hbox_label)
        ipage = self.notebook.append_page(vbox_page, hbox_label)
        self.notebook.set_tab_reorderable(vbox_page, True)

        # Save properties
        self.notebook_pages[file_path] = {
            "ipage": ipage,
            "page": vbox_page,
            "label": label_page,
            "button_save": button_save,
            "source_buffer": source_buffer, 
            "source_editor": source_editor,
            "is_modified": False
        }
        self.set_label_page()
        self.show_all()
        self.notebook.set_current_page(ipage)
        self.set_current_page(file_path)

        # self.dump_notebook()

    def on_button_save_clicked(self, widget):
        """ Sauvegarde du fichier """
        self.save_file(self.current_file)
    
    def on_button_close_clicked(self, sender, page):
        """ Fermeture de l'onglet de la page """
        pagenum = self.notebook.page_num(page)
        file_path = self.current_file
        for file in self.notebook_pages:
            if self.notebook_pages[file]["ipage"] == pagenum:
                file_path = file

        if self.confirm_if_modified(file_path) :
            self.notebook.remove_page(pagenum)
            del self.notebook_pages[file_path]
            if len(self.notebook_pages) == 0 : self.current_file = ""
            self.refresh_list_selection()
        
        # self.dump_notebook()        

    def dump_notebook(self):
        """ trace notebook """
        print ("<<< NOTEBOOK [" + self.current_file + "] >>>")
        for file in self.notebook_pages:
            print ("[" + file + "]")
            pprint (self.notebook_pages[file])

    def set_label_page(self):
        if len(self.current_file) > 20 : 
            label = "..." + self.current_file[-20:] 
        else: 
            label = self.current_file
        if self.is_modified():
            label = label + " *"
        self.notebook_pages[self.current_file]["label"].set_text(label)

    def on_check_crlf_toggled(self, button):
        """ gestion retour à la ligne """
        if button.get_active() :
            self.get_source_editor().set_wrap_mode(Gtk.WrapMode.WORD)
        else:
            self.get_source_editor().set_wrap_mode(Gtk.WrapMode.NONE)
    
    def on_switch_page(self, notebook, page, data):
        """ Click sur l'onglet d'une page """
        for file in self.notebook_pages:
            if self.notebook_pages[file]["page"] == page:
                self.set_current_page(file)                

        # self.dump_notebook()

    def set_current_page(self, file_path):
        """ Positionnement sur la page correspondant à file_path """
        self.current_file = file_path
        # Mise à jour sélection dans la listebox
        self.refresh_list_selection()

    def get_source_editor(self):
        return self.notebook_pages[self.current_file]["source_editor"]
    def get_source_buffer(self):
        return self.notebook_pages[self.current_file]["source_buffer"]
    def get_notebook_current_page(self):
        return self.notebook_pages[self.current_file]["page"]
    def get_notebook_current_n_page(self):
        return self.notebook_pages[self.current_file]["ipage"]
    def is_modified(self):
        return self.notebook_pages[self.current_file]["is_modified"]
    def set_modified(self, value):
        self.notebook_pages[self.current_file]["is_modified"] = value
        self.set_label_page()
        if value:
            self.notebook_pages[self.current_file]["button_save"].set_sensitive(True)
        else:
            self.notebook_pages[self.current_file]["button_save"].set_sensitive(False)

    def is_wrap_mode(self):
        return self.notebook_pages[self.current_file]["is_wrap_mode"]

    def get_current_line(self):
        """ Obtenir la ligne courante de l'éditeur """
        iter = self.get_source_buffer().get_iter_at_mark(self.get_source_buffer().get_insert())
        end = iter.copy()
        end.forward_line()
        start = end.copy()
        start.backward_line()
        sline = self.get_source_buffer().get_text(start, end, False)
        # passage ligne suivante
        iter.forward_lines(1)
        self.get_source_buffer().place_cursor(iter)
        return sline.replace("\n", "")

    def on_textbuffer_changed(self, widget):
        """ Le texte a été modifié """
        self.set_modified(True)

    def paste_current_line(self):
        """ on colle la ligne courante dans le terminal """
        # Sélection de la ligne courante, copie dans le clipboard et coller dans le terminal
        if self.current_file in self.notebook_pages:
            sline = self.get_current_line()
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
            self.paste_current_line
        if args[2] == 115 : # ctrl+S
            if self.is_modified() : self.notebook_pages[self.current_file]["button_save"].clicked()

    def on_button_menu_clicked(self, button):
        self.popover.set_relative_to(button)
        self.popover.show_all()
        self.popover.popup()

    def on_popover_menu_clicked(self, button, button_name):
        print("popover", button_name)

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
    
    # GESTION DES FICHIERS
    def select_file(self, file_path):
        """ sélection d'un fichier dans la liste """ 
        if file_path in self.notebook_pages:
            # self.set_current_page(file_path)
            self.notebook.set_current_page(self.notebook_pages[file_path]["ipage"])
        else:
            self.add_page_notebook(file_path)

    def save_file(self, path_file):
        iStart, iEnd = self.get_source_buffer().get_bounds()
        data = self.get_source_buffer().get_text(iStart, iEnd, True)

        pathfile = self.current_file
        # BACKUP du fichier.bak dans le répertoire gedian
        if self.current_file.find(self.gedian_directory) == -1:
            # création de la même arborescence sous gedian
            # pathfile = os.path.abspath(".") + self.current_file
            pathfile = self.gedian_directory + self.current_file          
            directory = os.path.dirname(pathfile)
            if not os.path.exists(directory):
                os.makedirs(directory)
        cmd = "cp '{}' '{}.bak'".format(self.current_file, pathfile)
        subprocess.Popen(shlex.split(cmd))

        # RECOPIE du fichier modifié dans gedian
        if self.current_file.find(self.gedian_directory) == -1:
            with open(pathfile, "w") as f:           
                f.write(data) 

        # CTRL DROIT d'écriture
        dir_file = os.path.dirname(self.current_file)
        if os.access(dir_file, os.W_OK):
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
        self.set_modified(False)

    def get_resource_path(self, rel_path):
        dir_of_py_file = os.path.dirname(__file__)
        rel_path_to_resource = os.path.join(dir_of_py_file, rel_path)
        abs_path_to_resource = os.path.abspath(rel_path_to_resource)
        return os.path.expanduser(abs_path_to_resource)

    def on_close(self, event, data):
        """ Fermeture de l'application """
        # Recherche fichiers modifiés
        is_ok= True
        for file_path in self.notebook_pages:
            if self.notebook_pages[file_path]["is_modified"]:
                is_ok = self.confirm_if_modified(file_path)
        
        return False if is_ok else True

    def on_button_about_clicked(self, widget):
        """
        La fenêtre About...
        """
        about = Gtk.AboutDialog()
        about.set_transient_for(self)
        about.set_title(APPLICATION_NAME)
        about.set_program_name(APPLICATION_NAME)
        about.set_version("20.6.17")
        about.set_copyright("pbillerot@github.com")
        about.set_comments("Editeur des fichiers d'un système DEBIAN")
        about.set_website("https://github.com/pbillerot/gedian")
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(get_resource_path("./gedian.svg"))
        about.set_logo(pixbuf)
        with open(get_resource_path("LICENSE"), 'r') as file:
            about.set_license(file.read())
        about.connect("response", lambda d, r: d.destroy())
        about.show()

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
parser.add_argument('-directory', help="Répertoire de GEDIAN (~/local/share/gedian par défaut)")
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
elif args.directory:
    win = Gedian(gedian_directory=args.directory)
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
else:
    win = Gedian()
    win.connect("destroy", Gtk.main_quit)
    win.connect("delete-event", win.on_close)
    win.show_all()
    Gtk.main()
