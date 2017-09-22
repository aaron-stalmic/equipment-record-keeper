""" Database functions module for Stalmic Equipment Record Keeper."""

from contextlib import contextmanager
from tkinter import messagebox
import tkinter as tk
import sys
import csv
import re
import dateutil.parser
import pyodbc
from config import get_config
from gui import TITLE


def open_connection(connect_string):
    """ Opens an ODBC connection and returns the connection using a connect
    string."""
    try:
        connection = pyodbc.connect(connect_string)
    except:
        tk.messagebox.showerror(TITLE, "Could not connect to database.")
        return

    connection.setdecoding(pyodbc.SQL_CHAR, encoding='utf-8')
    connection.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-8')
    connection.setencoding('utf-8')
    return connection


@contextmanager
def yield_connection(connect_string, commit=False):
    """ Yields a connection generator so that the connection can be used with
    the with syntax."""
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
    """ Yields a connection to the Stalmic SQL server."""
    config = get_config()
    connect_string = 'DRIVER={{SQL Server}};SERVER={};DATABASE={};\
            UID={};PWD={}'.format(config[0], config[1],
                                  config[2], config[3])
    return yield_connection(connect_string, commit)


def get_stalmic_connection():
    """ Returns a connection to the Stalmic SQL server."""
    config = get_config()
    connect_string = 'DRIVER={{SQL Server}};SERVER={};DATABASE={};\
            UID={};PWD={}'.format(config[0], config[1],
                                  config[2], config[3])
    return open_connection(connect_string)


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


def get_value_by_id(id, table, column, id_column):
    assert (table == 'Customer' or table == 'Inventory' or table == 'Vendor' or
            table == 'EquipmentRecords'), ("Table name not in whitelist "
                                           "(Customer, Inventory, Vendor).")
    assert (column == 'CustomerNum' or column == 'InventoryNum' or
            column == 'VendorNum' or column == 'SerialNumber'), (
            "Column name not in whitelist "
            "(CustomerNum, InventoryNum, VendorNum).")
    assert (id_column == 'CustomerID' or id_column == 'InventoryID' or
            id_column == 'VendorID' or id_column == 'EquipmentRecordsID'), (
            "ID column name not in whitelist "
            "(CustomerID, InventoryID, VendorID).")
    with stalmic_connection() as cursor:
        command = 'SELECT {} FROM {} WHERE {} = ?'.format(column, table,
                                                          id_column)
        print(command, id)
        cursor.execute(command, id)
        try:
            return cursor.fetchone()[0]
        except TypeError:
            return None


def write_to_notes():
    with stalmic_connection() as cursor:
        command = '''
        UPDATE Note SET NoteText = '--EQUIPMENT--'
        WHERE NoteText LIKE '--EQUIPMENT--%'
        '''
        cursor.execute(command)
        command = '''
        SELECT RecordID, NoteID, NoteText FROM Note
        WHERE ModuleCode = 'Customer' AND NoteText LIKE '--EQUIPMENT--%'
        '''
        cursor.execute(command)
        _notes = cursor.fetchall()
        notes = {}
        for item in _notes:
            notes[item[0]] = [item[1], item[2]]

        command = '''
        SELECT CustomerID, InventoryNum, SerialNumber, InvoiceDate,
        StalmicPurchase, ServiceAgreement
        FROM EquipmentRecords
        INNER JOIN Inventory
        ON EquipmentRecords.InventoryID = Inventory.InventoryID
        '''
        cursor.execute(command)
        equipment = cursor.fetchall()
    for record in equipment:
        note = "\n{} - S/N {},  purchased {}\n    ".format(record[1], record[2],
        record[3].strftime('%#m/%#d/%y'))
        if record[4]:
            note += "StalPur"
        else:
            note += "NOT STALPUR"
        if record[5]:
            note += "  ServAgr"
        else:
            note += "  NO SERVAGR"
        try:
            notes[record[0]][1] += note
        except KeyError:
            notes[record[0]] = [False, "--EQUIPMENT--" + note]

    with stalmic_connection(True) as cursor:
        for x in notes:
            if not notes[x][0]:
                command = '''
                INSERT INTO Note (ModuleCode, RecordID, NoteText, SendToDevice,
                AlwaysSendToDevice, NoteDate)
                VALUES ('Customer', ?, ?, 1, 1, GETDATE())
                '''
                cursor.execute(command, (x, notes[x][1]))
            else:
                command = '''
                UPDATE Note
                SET NoteText = ?
                WHERE NoteID = ?
                '''
                cursor.execute(command, (notes[x][1], notes[x][0]))
    # Clean up
    with stalmic_connection(True) as cursor:
        command = '''
        DELETE FROM Note
        WHERE NoteText = '--EQUIPMENT--'
        '''
        cursor.execute(command)

    tk.messagebox.showinfo(TITLE, "Successfully pushed.")


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

    def get_item(self, connection=False):
        command = '''
        SELECT InventoryNum FROM Inventory WHERE InventoryID = ?
        '''
        if connection:
            cursor = connection.cursor()
            cursor.execute(command, self.InventoryID)
            try:
                return cursor.fetchone()[0]
            except TypeError:
                return None
        with stalmic_connection() as cursor:
            cursor.execute(command, self.InventoryID)
            try:
                return cursor.fetchone()[0]
            except TypeError:
                return None

    def get_customer(self, connection=False):
        command = '''
        SELECT CustomerNum FROM Customer WHERE CustomerID = ?
        '''
        if connection:
            cursor = connection.cursor()
            cursor.execute(command, self.CustomerID)
            try:
                return cursor.fetchone()[0]
            except TypeError:
                return None
        with stalmic_connection() as cursor:
            cursor.execute(command, self.CustomerID)
            try:
                return cursor.fetchone()[0]
            except TypeError:
                return None

    def get_vendor(self, connection=False):
        command = '''
        SELECT VendorNum FROM Vendor WHERE VendorID = ?
        '''
        if connection:
            cursor = connection.cursor()
            cursor.execute(command, self.VendorID)
            try:
                return cursor.fetchone()[0]
            except TypeError:
                return None
        with stalmic_connection() as cursor:
            cursor.execute(command, self.VendorID)
            try:
                return cursor.fetchone()[0]
            except TypeError:
                return None

    def get_record(self, connection=False):
        try:
            invdate = self.InvoiceDate.strftime("%m/%d/%Y")
        except AttributeError:
            invdate = None
        try:
            purdate = self.PurchaseDate.strftime("%m/%d/%Y")
        except AttributeError:
            purdate = None
        return (self.ID, self.get_item(connection), self.SerialNumber,
                self.StalmicPurchase, self.ServiceAgreement,
                self.get_customer(connection), invdate,
                self.get_vendor(connection), purdate)

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

    def edit_record(self):
        command = 'UPDATE EquipmentRecords SET'
        vars = []
        var_string = []
        if self.InventoryID:
            vars.append(self.InventoryID)
            var_string.append('InventoryID = ?')
        if self.CustomerID:
            vars.append(self.CustomerID)
            var_string.append('CustomerID = ?')
        if self.VendorID:
            vars.append(self.VendorID)
            var_string.append('VendorID = ?')
        if self.PurchaseDate:
            vars.append(self.PurchaseDate)
            var_string.append('PurchaseDate = ?')
        if self.InvoiceDate:
            vars.append(self.InvoiceDate)
            var_string.append('InvoiceDate = ?')
        if self.SerialNumber:
            vars.append(self.SerialNumber)
            var_string.append('SerialNumber = ?')
        # Have to use "is not None" here because otherwise we can't change
        # these to False.
        if self.StalmicPurchase is not None:
            vars.append(self.StalmicPurchase)
            var_string.append('StalmicPurchase = ?')
        if self.ServiceAgreement is not None:
            vars.append(self.ServiceAgreement)
            var_string.append('ServiceAgreement = ?')
        command += ' ' + ', '.join(var_string)
        command += ' WHERE EquipmentRecordsID = ?'
        vars.append(self.ID)
        if len(vars) > 1:
            with stalmic_connection(True) as cursor:
                cursor.execute(command, vars)

    def __repr__(self):
        return str((self.ID, self.InventoryID, self.SerialNumber,
                    self.StalmicPurchase, self.ServiceAgreement,
                    self.CustomerID, self.InvoiceDate, self.VendorID,
                    self.PurchaseDate))


class EquipmentList:
    def __init__(self, CustomerID=None, InventoryID=None, SerialNumber=None,
                 CustomerNum=None, InventoryNum=None, StalmicPurchase=None,
                 ServiceAgreement=None, ID=None):
        self.CustomerID = CustomerID
        self.InventoryID = InventoryID
        self.SerialNumber = SerialNumber
        self.StalmicPurchase = StalmicPurchase
        self.ServiceAgreement = ServiceAgreement
        # These are for searches:
        self.CustomerNum = CustomerNum
        self.InventoryNum = InventoryNum
        self.ID = ID
        # Build the SELECT statement.
        equipment_command = '''
        SELECT EquipmentRecords.InventoryID, SerialNumber, StalmicPurchase,
        ServiceAgreement, EquipmentRecords.CustomerID, InvoiceDate,
        EquipmentRecords.VendorID, PurchaseDate, EquipmentRecordsID
        FROM EquipmentRecords
        LEFT JOIN Customer
        ON EquipmentRecords.CustomerID = Customer.CustomerID
        LEFT JOIN Inventory
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
        if self.ID:
            vars.append(self.ID)
            var_string.append('EquipmentRecordsID = ?')
        vars = tuple(vars)
        # Join them together with AND.
        var_string = ' AND '.join(var_string)
        if len(var_string) > 0:
            equipment_command += 'WHERE '
            equipment_command += var_string
        # Sort by Customer for now.
        equipment_command += '''
        ORDER BY CASE WHEN CustomerNum IS NULL THEN 1 ELSE 0 END, CustomerNum,
        CASE WHEN InventoryNum IS NULL THEN 1 ELSE 0 END, InventoryNum,
        CASE WHEN InvoiceDate IS NULL THEN 1 ELSE 0 END, InvoiceDate,
        CASE WHEN SerialNumber IS NULL OR SerialNumber = '' THEN 1 ELSE 0 END,
        SerialNumber
        '''
        with stalmic_connection() as cursor:
            cursor.execute(equipment_command, vars)
            self.equipment = cursor.fetchall()
        self.equipment = [EquipmentRecord(*x) for x in self.equipment]

    def get_equipment(self, connection=False):
        return [x.get_record(connection) for x in self.equipment]
        

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


def import_sales_csv(filename):
    """ Imports sales data from a CSV."""
    with open(filename, newline='', encoding='utf-8-sig') as file:
        reader = list(csv.reader(file))
    for item in reader:
        if item[0] == "Invoice":
            inv_date = None if item[1] == '' else dateutil.parser.parse(item[1])
            customer_id = get_id(item[2], 'Customer', 'CustomerNum')
            inv_num = re.search(r'(.+?)(?= \()', item[3])
            inv_num = inv_num.group(0)
            item_id = get_id(inv_num, 'Inventory', 'InventoryNum')
            serial = item[5].split(',')
            for i in range(int(item[4])):
                try:
                    serial[i]
                except IndexError:
                    serial.append(None)
                if customer_id is not None and item_id is not None: 
                    print(item)
                    e = EquipmentRecord(item_id, serial[i], True, False,
                                        customer_id, inv_date)
                    e.add_record()
    for item in reader:
        if item[0] == 'Invoice':
            if int(item[4]) < 0:
                serial = item[5].split(',')
                for i in range(-int(item[4])):
                    try:
                        serial[i]
                    except IndexError:
                        pass
                    else:
                        inv_num = re.search(r'(.+?)(?= \()', item[3])
                        inv_num = inv_num.group(0)
                        e = EquipmentList(InventoryNum=inv_num,
                                          SerialNumber=serial[i],
                                          CustomerNum=item[2])
                        e = e.get_equipment()
                        for j in e:
                            if (dateutil.parser.parse(j[6]) <
                                dateutil.parser.parse(item[1])):
                                print("REMOVING", item)
                                with stalmic_connection(True) as cursor:
                                    command = '''
                                    DELETE FROM EquipmentRecords
                                    WHERE EquipmentRecordsID = ?'''
                                    cursor.execute(command, j[0])


def import_purchases_csv(filename):
    """ Imports purchase data from a CSV."""
    with open(filename, newline='', encoding='utf-8-sig') as file:
        reader = list(csv.reader(file))
    for item in reader:
        if item[0] == 'Bill' and item[1] != '':
            pur_date = dateutil.parser.parse(item[1])
            serial = item[5].split(',')
            for serial_number in serial:
                if serial_number == '':
                    break
                e = EquipmentList(SerialNumber=serial_number)
                e = e.get_equipment()
                if len(e) > 0:
                    print(item)
                for i in e:
                    with stalmic_connection(True) as cursor:
                        command = '''
                        UPDATE EquipmentRecords
                        SET PurchaseDate = ?
                        WHERE EquipmentRecordsID = ?'''
                        cursor.execute(command, (pur_date, i[0]))
