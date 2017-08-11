import pyodbc
import itertools
from contextlib import contextmanager
from config import get_config
import tkinter as tk
from tkinter import messagebox
from gui import TITLE
import sys


@contextmanager
def open_connection(connect_string, commit=False):
    try:
        connection = pyodbc.connect(connect_string)
    except:
        tk.messagebox.showerror(TITLE, "Could not connect to database.")
        return

    connection.setdecoding(pyodbc.SQL_CHAR, encoding='utf-8')
    connection.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-8')
    connection.setencoding('utf-8')
    cursor = connection.cursor()
    try:
        yield cursor
    except pyodbc.DatabaseError as err:
        error, = err.args
        sys.stderr.write(error.message)
        cursor.execute("ROLLBACK")
        raise err
    else:
        if commit:
            cursor.execute("COMMIT")
        else:
            try:
                cursor.execute("ROLLBACK")
            except:
                pass
    finally:
        connection.close()


def stalmic_connection(commit=False):
    config = get_config()
    connect_string = 'DRIVER={{SQL Server}};SERVER={};DATABASE={};\
            UID={};PWD={}'.format(config[0], config[1],
                                  config[2], config[3])
    return open_connection(connect_string, commit)


def get_id(value, table, column):
    # Prevent SQL injection:
    assert table == 'Customer' or table == 'Inventory' or table == 'Vendor',\
        "Table name not in whitelist (Customer, Inventory, Vendor)."
    assert (column == 'CustomerNum' or column == 'InventoryNum' or
            column == 'VendorNum'), ("Column name not in whitelist "
                                     "(CustomerNum, InventoryNum, VendorNum).")
    with stalmic_connection() as cursor:
        command = 'SELECT * FROM {} WHERE {} = ?'.format(table, column)
        cursor.execute(command, value)
        try:
            return cursor.fetchone()[0]
        except TypeError:
            return None


class EquipmentRecord:
    def __init__(self, InventoryID, SerialNumber=None, StalmicPurchase=True,
                 ServiceAgreement=None, CustomerID=None, InvoiceDate=None,
                 VendorID=None, PurchaseDate=None, ID=None):
        self.InventoryID = InventoryID
        self.SerialNumber = SerialNumber
        if StalmicPurchase is None:
            self.StalmicPurchase = False
        else:
            self.StalmicPurchase = StalmicPurchase
        if ServiceAgreement is None:
            self.ServiceAgreement = False
        else:
            self.ServiceAgreement = ServiceAgreement
        self.CustomerID = CustomerID
        self.InvoiceDate = InvoiceDate
        self.VendorID = VendorID
        self.PurchaseDate = PurchaseDate
        self.ID = ID

    def get_item(self):
        with stalmic_connection() as cursor:
            command = '''
            SELECT InventoryNum FROM Inventory WHERE InventoryID = ?
            '''
            cursor.execute(command, self.InventoryID)
            try:
                return cursor.fetchone()[0]
            except TypeError:
                return None

    def get_customer(self):
        with stalmic_connection() as cursor:
            command = '''
            SELECT CustomerNum FROM Customer WHERE CustomerID = ?
            '''
            cursor.execute(command, self.CustomerID)
            try:
                return cursor.fetchone()[0]
            except TypeError:
                return None

    def get_vendor(self):
        with stalmic_connection() as cursor:
            command = '''
            SELECT VendorNum FROM Vendor WHERE VendorID = ?
            '''
            cursor.execute(command, self.VendorID)
            try:
                return cursor.fetchone()[0]
            except TypeError:
                return None

    def get_record(self):
        try:
            invdate = self.InvoiceDate.strftime("%m/%d/%Y")
        except AttributeError:
            invdate = None
        try:
            purdate = self.PurchaseDate.strftime("%m/%d/%Y")
        except AttributeError:
            purdate = None
        return (self.ID, self.get_item(), self.SerialNumber,
                self.StalmicPurchase, self.ServiceAgreement,
                self.get_customer(), invdate, self.get_vendor(), purdate)

    def add_record(self):
        with stalmic_connection(True) as cursor:
            command = '''
            INSERT INTO EquipmentRecords VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            '''
            cursor.execute(command, (self.InventoryID, self.CustomerID,
                                     self.VendorID, self.PurchaseDate,
                                     self.InvoiceDate, self.SerialNumber,
                                     self.StalmicPurchase,
                                     self.ServiceAgreement))

    def __repr__(self):
        return str((self.ID, self.InventoryID, self.SerialNumber,
                    self.StalmicPurchase, self.ServiceAgreement,
                    self.CustomerID, self.InvoiceDate, self.VendorID,
                    self.PurchaseDate))


class EquipmentList:
    def __init__(self, CustomerID=None, InventoryID=None, SerialNumber=None,
                 CustomerNum=None, InventoryNum=None, StalmicPurchase=None,
                 ServiceAgreement=None):
        self.CustomerID = CustomerID
        self.InventoryID = InventoryID
        self.SerialNumber = SerialNumber
        self.StalmicPurchase = StalmicPurchase
        self.ServiceAgreement = ServiceAgreement
        # These are for searches:
        self.CustomerNum = CustomerNum
        self.InventoryNum = InventoryNum
        # Build the SELECT statement.
        equipment_command = '''
        SELECT EquipmentRecords.InventoryID, SerialNumber, StalmicPurchase,
        ServiceAgreement, EquipmentRecords.CustomerID, InvoiceDate,
        EquipmentRecords.VendorID, PurchaseDate, EquipmentRecordsID
        FROM EquipmentRecords
        INNER JOIN Customer
        ON EquipmentRecords.CustomerID = Customer.CustomerID
        INNER JOIN Inventory
        ON EquipmentRecords.InventoryID = Inventory.InventoryID
        '''
        # Build our WHERE statement if there are variables.
        vars = []
        var_string = []
        if self.CustomerNum:
            vars.append(self.CustomerNum)
            var_string.append('CustomerNum LIKE ?')
        elif self.CustomerID:
            vars.append(self.CustomerID)
            var_string.append('CustomerID = ?')
        if self.InventoryNum:
            vars.append(self.InventoryNum)
            var_string.append('InventoryNum LIKE ?')
        elif self.InventoryID:
            vars.append(self.InventoryID)
            var_string.append('InventoryID = ?')
        if self.SerialNumber:
            vars.append(self.SerialNumber)
            var_string.append('SerialNumber LIKE ?')
        if self.ServiceAgreement:
            vars.append(self.ServiceAgreement)
            var_string.append('ServiceAgreement = ?')
        if self.StalmicPurchase:
            vars.append(self.StalmicPurchase)
            var_string.append('StalmicPurchase = ?')
        vars = tuple(vars)
        # Join them together with AND.
        var_string = ' AND '.join(var_string)
        if len(var_string) > 0:
            equipment_command += 'WHERE '
            equipment_command += var_string
        # Sort by Customer for now.
        equipment_command += '\nORDER BY CustomerNum'
        with stalmic_connection() as cursor:
            cursor.execute(equipment_command, vars)
            self.equipment = cursor.fetchall()
        self.equipment = [EquipmentRecord(*x) for x in self.equipment]

    def get_equipment(self):
        return [x.get_record() for x in self.equipment]

    def get_string(self):
        columns = [("ID", "Model No.", "Serial No.", "Stalmic Pur.",
                    "Service Agr.", "Customer", "Inv. Date", "Vendor",
                    "Pur. Date")]
        equipment = columns + self.get_equipment()
        widths = [0] * len(equipment[0])
        # Get the max widths for the columns
        for entry in equipment:
            for i in range(len(entry)):
                if len(str(entry[i])) > widths[i]:
                    widths[i] = len(str(entry[i]))
        # Now let's print.
        equipment_string = ""
        for entry in equipment:
            for i in range(0, len(entry)-1):
                equipment_string += str(entry[i]).ljust(widths[i]+2)
            # Last column will have no spacing.
            equipment_string += str(entry[len(entry)-1]).ljust(
                                                        widths[len(entry)-1])
            equipment_string += "\n"
        return equipment_string

    def __repr__(self):
        return str(self.equipment)
