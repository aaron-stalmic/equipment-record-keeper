import tkinter as tk
from tkinter import ttk


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
            self.delete(self.position, END)
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
            self.delete(0, END)
            self.insert(0, self._hits[self._hit_index])
            self.select_range(self.position, END)
            try:
                desc.set(inventory[item.get()])
            except:
                desc.set('')

    def handle_keyrelease(self, event):
        """
        Event handler for the keyrelease event on this widget.
        """
        if event.keysym == 'BackSpace':
            self.delete(self.index(INSERT), END)
            self.position = self.index(END)
        if event.keysym == 'Left':
            if self.position < self.index(END):  # Delete the selection.
                self.delete(self.position, END)
            else:
                self.position = self.position - 1  # Delete one character.
                self.delete(self.position, END)
        if event.keysym == 'Right' or event.keysym == 'KP_Enter':
            self.position == self.index(END)  # Go to end (no selection)
        if len(event.keysym) == 1:
            self.autocomplete()


class MainApplication(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        self.customer = self.add_combobox("Customer", 0, 0)
        self.model = self.add_combobox("Model No.", 0, 1)
        self.serial = self.add_combobox("Serial No.", 0, 2)

    def add_combobox(self, label, r, c):
        tk.Label(self.parent, text=label).grid(row=r, column=c)
        combo = AutocompleteCombobox(self.parent)
        combo.grid(row=r+1, column=c)
        return combo


if __name__ == '__main__':
    root = tk.Tk()
    MainApplication(root)
    root.mainloop()
