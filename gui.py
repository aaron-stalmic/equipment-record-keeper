import tkinter as tk
from tkinter import ttk
from dbfunctions import *
from tkinter import font


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
            else:
                self.position = self.position - 1  # Delete one character.
                self.delete(self.position, tk.END)
        if event.keysym == 'Right' or event.keysym == 'KP_Enter':
            self.position == self.index(tk.END)  # Go to end (no selection)
        if len(event.keysym) == 1:
            self.autocomplete()


class ResultsWindow(tk.Frame):
    def __init__(self, parent, row, column, columnspan=1, sticky=None):
        tk.Frame.__init__(self, parent)
        self.canvas = tk.Canvas(parent, borderwidth=0)
        self.frame = tk.Frame(self.canvas)
        self.vsb = tk.Scrollbar(parent, orient='vertical',
                                command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        width, height = parent.grid_size()
        self.vsb.grid(row=height, column=width+1, sticky=tk.N+tk.S+tk.W)
        self.canvas.grid(row=row, column=column, columnspan=columnspan,
                         sticky=sticky)
        self.canvas.create_window((4, 4), window=self.frame, anchor='nw',
                                  tags='self.frame')
        self.frame.bind('<Configure>', self.onFrameConfigure)

    def populate(self, data):
        for widget in self.frame.winfo_children():
            widget.destroy()
        for r in range(len(data)):
            if r != 0:
                tk.Button(self.frame, text="Edit").grid(row=r, column=0)
            for c in range(len(data[r])):
                item = tk.Label(self.frame, text=str(data[r][c]))
                if r == 0:
                    f = font.Font(item, item.cget('font'))
                    f.configure(underline = True)
                    item.configure(font=f)
                item.grid(row=r, column=c+1, padx=5)


    def onFrameConfigure(self, event):
        '''Reset the scroll region to encompass the inner frame'''
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))


class MainApplication(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent
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
        self.invdate = tk.Entry(self.parent).grid(row=1, column=3)
        self._purdate = tk.Label(self.parent, text="Purchase Date")
        self._purdate.grid(row=0, column=4)
        self.purdate = tk.Entry(self.parent).grid(row=1, column=4)
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
        # Add a search button to the end.
        self.search_button = tk.Button(self.parent, text="Search",
                                       command=self.search)
        self.search_button.grid(row=1, column=width)
        # Big results box. Needs to span past the search button.
        self.results = ResultsWindow(self.parent, row=height, column=0,
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
                if location[0] == 'Inventory':
                    location[0] = "Inventory WHERE InventoryNum LIKE '7%'"
                command = 'SELECT {} FROM {}'.format(location[1], location[0])
            except IndexError:
                return []
            else:
                cursor.execute(command)
                values = cursor.fetchall()
                return [item for sublist in values for item in sublist]

    def add_combobox(self, label, r, c, location=[]):
        # Create a StringVar in the Value dictionary
        self.value[label] = tk.StringVar()
        tk.Label(self.parent, text=label).grid(row=r, column=c)
        completion_list = self.get_lists(location)
        combo = AutocompleteCombobox(self.parent,
                                     textvariable=self.value[label],
                                     values=completion_list)
        combo.set_completion_list(completion_list)
        combo.grid(row=r+1, column=c)
        return combo

    def search(self):
        # Make the search more user friendly. Searches for items that contain
        # search term.
        columns = [("ID", "Model No.", "Serial No.", "Stalmic Pur.",
                    "Service Agr.", "Customer", "Inv. Date", "Vendor",
                    "Pur. Date")]
        customer = self.value["Customer"].get()
        customer = customer.split()
        customer = '%' + '%'.join(customer) + '%'
        item = self.value["Model No."].get()
        item = item.split()
        item = '%' + '%'.join(item) + '%'
        serial = self.value["Serial No."].get()
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
        customer = self.value["Customer"].get()
        item = self.value["Model No."].get()
        serial = self.value["Serial No."].get()
        pur = self.is_purchase.get()
        serv = self.is_service.get()


if __name__ == '__main__':
    root = tk.Tk()
    MainApplication(root)
    root.mainloop()
