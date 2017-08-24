import tkinter as tk
from tkinter import ttk
import dateutil.parser
from dbfunctions import *
from tkinter import font

TITLE = "Equipment Records"


class AutocompleteCombobox(ttk.Combobox):
    def set_completion_list(self, completion_list):
        """
        Use our completion list as our drop down selection menu, arrows move
        through menu.
        """
        self._completion_list = sorted(completion_list, key=str.lower)
        self._hits = []
        self._hit_index = 0
        self.position = 0
        self.bind('<KeyRelease>', self.handle_keyrelease)
        self['values'] = self._completion_list  # Setup our popup menu.

    def autocomplete(self, delta=0):
        """
        Autocomplete the Combobox, delta may be 0/1/-1 to cycle through
        possible hits.
        """
        # Need to delete selection otherwise we would fix current position.
        if delta:
            self.delete(self.position, tk.END)
        else:
            self.position = len(self.get())
        _hits = []
        for element in self._completion_list:
            if element.lower().startswith(self.get().lower()):
                _hits.append(element)
        # If we have a new hit list, keep this in mind.
        if _hits != self._hits:
            self._hit_index = 0
            self._hits = _hits
        # Only allow cycling if we are in a known hit list.
        if _hits == self._hits and self._hits:
            self._hit_index = (self._hit_index + delta) % len(self._hits)
        # Perform the autocompletion
        if self._hits:
            self.delete(0, tk.END)
            self.insert(0, self._hits[self._hit_index])
            self.select_range(self.position, tk.END)

    def handle_keyrelease(self, event):
        """
        Event handler for the keyrelease event on this widget.
        """
        if event.keysym == 'BackSpace':
            self.delete(self.index(tk.INSERT), tk.END)
            self.position = self.index(tk.END)
        if event.keysym == 'Left':
            if self.position < self.index(tk.END):  # Delete the selection.
                self.delete(self.position, tk.END)
            # else
            #    self.position = self.position - 1  # Delete one character.
            #    self.delete(self.position, tk.END)
        if event.keysym == 'Right' or event.keysym == 'KP_Enter':
            self.position == self.index(tk.END)  # Go to end (no selection)
        if len(event.keysym) == 1:
            self.autocomplete()


class ResultsWindow(tk.Frame):
    def __init__(self, parent, main, row, column, columnspan=1, sticky=None):
        self.parent = parent
        self.main = main
        tk.Frame.__init__(self, self.parent)
        self.canvas = tk.Canvas(self.parent, borderwidth=0)
        self.frame = tk.Frame(self.canvas)
        self.vsb = tk.Scrollbar(self.parent, orient='vertical',
                                command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        width, height = self.parent.grid_size()
        self.vsb.grid(row=height, column=width+1, sticky=tk.N+tk.S+tk.W)
        self.canvas.grid(row=row, column=column, columnspan=columnspan,
                         sticky=sticky)
        self.canvas.create_window((4, 4), window=self.frame, anchor='nw',
                                  tags='self.frame')
        self.canvas.bind_all('<MouseWheel>', self._on_mousewheel)
        self.frame.bind('<Configure>', self.onFrameConfigure)

    def populate(self, data):
        for widget in self.frame.winfo_children():
            widget.destroy()
        for r in range(len(data)):
            if r != 0:
                editbutton = tk.Button(self.frame, text="Edit",
                                       command=lambda x=r: self.edit(
                                                                data[x][0]))
                editbutton.grid(row=r, column=0)
            for c in range(len(data[r])):
                item = tk.Label(self.frame, text=str(data[r][c]))
                if r == 0:
                    f = font.Font(item, item.cget('font'))
                    f.configure(underline=True)
                    item.configure(font=f)
                if data[r][c] is True:
                    item.configure(text='YES', foreground='green')
                elif data[r][c] is False:
                    item.configure(text='NO', foreground='red')
                item.grid(row=r, column=c+1, padx=5)

    def onFrameConfigure(self, event):
        '''Reset the scroll region to encompass the inner frame'''
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*event.delta//120), 'units')

    def edit(self, id):
        EditWindow(self, self.main, id)


class MainApplication(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        # Make a menu bar for the sync command.
        self.menubar = tk.Menu(self.parent)
        self.filemenu = tk.Menu(self.menubar, tearoff=0)
        self.filemenu.add_command(label='Push to Customer Notes',
                                  command=write_to_notes)
        self.menubar.add_cascade(label='Database', menu=self.filemenu)
        self.parent.config(menu=self.menubar)
        # configure row and column weights.
        # Make a dictionary for the combobox values.
        self.value = {}
        self.model = self.add_combobox("Model No.", 0, 0,
                                       ['Inventory', 'InventoryNum'])
        self.serial = self.add_combobox("Serial No.", 0, 1,
                                        ['EquipmentRecords', 'SerialNumber'])
        self.customer = self.add_combobox("Customer", 0, 2,
                                          ['Customer', 'CustomerNum'])
        self._invdate = tk.Label(self.parent, text="Invoice Date")
        self._invdate.grid(row=0, column=3)
        self.value["Invoice Date"] = tk.StringVar()
        self.invdate = tk.Entry(self.parent,
                                textvariable=self.value["Invoice Date"]).grid(
                                row=1, column=3)
        self._purdate = tk.Label(self.parent, text="Purchase Date")
        self._purdate.grid(row=0, column=4)
        self.value["Purchase Date"] = tk.StringVar()
        self.purdate = tk.Entry(self.parent,
                                textvariable=self.value["Purchase Date"]).grid(
                                row=1, column=4)
        # TODO: Implement TRI-STATE VALUE for checkboxes.
        self.is_purchase = tk.IntVar()
        self._is_purchase = tk.Checkbutton(self.parent, text="Stalmic Pur.",
                                           variable=self.is_purchase)
        self._is_purchase.grid(row=0, column=5)
        self.is_service = tk.IntVar()
        self._is_service = tk.Checkbutton(self.parent, text="Service Agr.",
                                          variable=self.is_service)
        self._is_service.grid(row=1, column=5)
        # Get the width and height after we've made our entry fields.
        width, height = self.parent.grid_size()
        self.add_button = tk.Button(self.parent, text="Add",
                                    command=self.add_entry, width=5)
        self.add_button.grid(row=1, column=width)
        # Add a search button to the end.
        self.search_button = tk.Button(self.parent, text="Search",
                                       command=self.search, width=5)
        self.search_button.grid(row=0, column=width)
        # Big results box. Needs to span past the search button.
        self.results = ResultsWindow(self.parent, self, row=height, column=0,
                                     columnspan=width+1,
                                     sticky=tk.W+tk.E+tk.N+tk.S)
        self.results.grid(row=height, column=0, columnspan=width+1,
                          sticky=tk.W+tk.E+tk.N+tk.S)
        # self.results = tk.Frame(self.parent)
        # self.results = tk.Text(self.parent, wrap=tk.NONE, font=('Consolas'))
        # self.results.grid(row=height, column=0, columnspan=(width+1),
        #                  sticky=tk.W+tk.E+tk.N)
        # self.scroll = tk.Scrollbar(self.parent)
        # self.xscroll = tk.Scrollbar(self.parent, orient=tk.HORIZONTAL)
        # self.scroll.config(command=self.results.yview)
        # self.xscroll.config(command=self.results.xview)
        # self.results.config(yscrollcommand=self.scroll.set,
        #                    xscrollcommand=self.xscroll.set)
        # self.xscroll.grid(row=height+1, column=0,
        #                  columnspan=width+1, sticky=tk.W+tk.E+tk.S)
        # self.scroll.grid(row=height, column=width+1, sticky=tk.N+tk.S+tk.W)
        # self.results.config(state=tk.DISABLED)
        for x in range(width):
            tk.Grid.columnconfigure(self.parent, x, weight=1)
        for y in range(2, height+1):
            tk.Grid.rowconfigure(self.parent, y, weight=1)

    def get_lists(self, location):
        with stalmic_connection() as cursor:
            try:
                command = '''
                SELECT {0} FROM {1}
                WHERE {0} <> '' AND {0} IS NOT NULL
                '''.format(location[1], location[0])
                if location[0] == 'Inventory':
                    command += "AND InventoryNum LIKE '7%'"
            except IndexError:
                return []
            else:
                cursor.execute(command)
                values = cursor.fetchall()
                return [item for sublist in values for item in sublist]

    def add_combobox(self, label, r, c, location=[]):
        completion_list = self.get_lists(location)
        # Create a StringVar in the Value dictionary
        self.value[label] = tk.StringVar()
        tk.Label(self.parent, text=label).grid(row=r, column=c)
        combo = AutocompleteCombobox(self.parent,
                                     textvariable=self.value[label],
                                     values=completion_list)
        combo.set_completion_list(completion_list)
        combo.grid(row=r+1, column=c, sticky=tk.W+tk.E)
        return combo

    def search(self):
        # Make the search more user friendly. Searches for items that contain
        # search term.
        columns = [("ID", "Model No.", "Serial No.", "Stalmic Pur.",
                    "Service Agr.", "Customer", "Inv. Date", "Vendor",
                    "Pur. Date")]
        customer = self.value["Customer"].get()
        if customer:
            customer = customer.split()
            customer = '%' + '%'.join(customer) + '%'
        item = self.value["Model No."].get()
        if item:
            item = item.split()
            item = '%' + '%'.join(item) + '%'
        serial = self.value["Serial No."].get()
        if serial:
            serial = serial.split()
            serial = '%' + '%'.join(serial) + '%'
        pur = self.is_purchase.get()
        serv = self.is_service.get()
        self.results.populate(columns+EquipmentList(CustomerNum=customer,
                                                    InventoryNum=item,
                                                    SerialNumber=serial,
                                                    StalmicPurchase=pur,
                                                    ServiceAgreement=serv
                                                    ).get_equipment())
        # self.results.config(state=tk.NORMAL)
        # self.results.delete(1.0, tk.END)
        # self.results.insert(tk.END,
        #                     EquipmentList(CustomerNum=customer,
        #                                   InventoryNum=item,
        #                                   SerialNumber=serial,
        #                                   StalmicPurchase=pur,
        #                                   ServiceAgreement=serv).get_string())
        # self.results.config(state=tk.DISABLED)

    def add_entry(self):
        # Get Customer, Item, Vendor IDs.
        customer = get_id(self.value["Customer"].get(),
                          'Customer', 'CustomerNum')
        item = get_id(self.value["Model No."].get(),
                      'Inventory', 'InventoryNum')
        serial = self.value["Serial No."].get()
        vendor = None
        try:
            invdate = dateutil.parser.parse(self.value["Invoice Date"].get())
        except ValueError:
            invdate = None
        try:
            purdate = dateutil.parser.parse(self.value["Purchase Date"].get())
        except ValueError:
            purdate = None
        pur = self.is_purchase.get()
        serv = self.is_service.get()
        EquipmentRecord(item, serial, pur, serv, customer,
                        invdate, vendor, purdate).add_record()


class EditWindow(MainApplication):
    def __init__(self, parent, main, id, *args, **kwargs):
        self.parent = parent
        self.main = main
        self.id = id
        # Get default values
        self.defaults = EquipmentList(ID=self.id).get_equipment()[0]
        self.window = tk.Toplevel(self.parent)
        self.window.grab_set()
        self.window.focus()
        self.window.update()
        self.window.minsize(300, self.window.winfo_height()-20)
        self.value = {}

        self.id_label = tk.Label(self.window, text="ID:")
        self.id_label.grid(row=0, column=0)
        self.id_num = tk.Label(self.window, text=self.id)
        self.id_num.grid(row=0, column=1)

        self.model = self.add_combobox("Model No.:", 1, 0,
                                       ['Inventory', 'InventoryNum'],
                                       self.defaults[1])
        self.serial = self.add_combobox("Serial No.:", 2, 0,
                                        ['EquipmentRecords', 'SerialNumber'],
                                        self.defaults[2])
        self.customer = self.add_combobox("Customer:", 3, 0,
                                          ['Customer', 'CustomerNum'],
                                          self.defaults[5])
        self.invdate = self.add_edit_field("Inv. Date:", 4, 0,
                                           self.defaults[6])
        self.purdate = self.add_edit_field("Pur. Date:", 5, 0,
                                           self.defaults[8])
        self.is_purchase = tk.IntVar()
        self._is_purchase = tk.Checkbutton(self.window, text="Stalmic Pur.",
                                           variable=self.is_purchase)
        if self.defaults[3]:
            self._is_purchase.select()
        self._is_purchase.grid(row=6, column=0, columnspan=2)
        self.is_service = tk.IntVar()
        self._is_service = tk.Checkbutton(self.window, text="Service Agr.",
                                          variable=self.is_service)
        if self.defaults[4]:
            self._is_service.select()
        self._is_service.grid(row=6, column=2)

        self.submit = tk.Button(self.window, text="Submit",
                                command=self.submit)
        self.submit.grid(row=7, column=1)
        self.delete = tk.Button(self.window, text="Delete",
                                command=self.delete)
        self.delete.grid(row=7, column=2)
        width, height = self.window.grid_size()
        for x in range(width):
            tk.Grid.columnconfigure(self.window, x, weight=1)
        for y in range(height):
            tk.Grid.rowconfigure(self.window, y, weight=1)

    def add_edit_field(self, label, r, c, default=None):
        self.value[label] = tk.StringVar()
        tk.Label(self.window, text=label).grid(row=r, column=c)
        entry = tk.Entry(self.window, textvariable=self.value[label])
        if default:
            self.value[label].set(default)
        entry.grid(row=r, column=c+1, columnspan=2, sticky=tk.W+tk.E)
        return entry

    def add_combobox(self, label, r, c, location=[], default=None):
        completion_list = self.get_lists(location)
        # Create a StringVar in the Value dictionary
        self.value[label] = tk.StringVar()
        tk.Label(self.window, text=label).grid(row=r, column=c)
        combo = AutocompleteCombobox(self.window,
                                     textvariable=self.value[label],
                                     values=completion_list)
        combo.set_completion_list(completion_list)

        if default:
            combo.set(default)
        combo.grid(row=r, column=c+1, columnspan=2, sticky=tk.W+tk.E)
        return combo

    def submit(self):
        customer = get_id(self.value["Customer:"].get(),
                          'Customer', 'CustomerNum')
        item = get_id(self.value["Model No.:"].get(),
                      'Inventory', 'InventoryNum')
        serial = self.value["Serial No.:"].get()
        vendor = None
        try:
            invdate = dateutil.parser.parse(self.value["Inv. Date:"].get())
        except ValueError:
            invdate = None
        try:
            purdate = dateutil.parser.parse(self.value["Pur. Date:"].get())
        except ValueError:
            purdate = None
        pur = self.is_purchase.get()
        serv = self.is_service.get()
        if tk.messagebox.askokcancel(TITLE, "Edit this entry?",
                                     parent=self.window):
            EquipmentRecord(item, serial, pur, serv, customer,
                            invdate, vendor, purdate, self.id).edit_record()
            self.main.search()

    def delete(self):
        if tk.messagebox.askokcancel(TITLE, "Delete this entry?",
                                     parent=self.window):
            with stalmic_connection(True) as cursor:
                command = '''
                DELETE FROM EquipmentRecords WHERE EquipmentRecordsID = ?'''
                cursor.execute(command, self.id)
            self.window.destroy()
            self.main.search()


if __name__ == '__main__':
    root = tk.Tk()
    root.geometry('1024x500')
    root.wm_title(TITLE)
    MainApplication(root)
    root.mainloop()
