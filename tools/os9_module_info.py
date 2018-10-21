#!/usr/bin/env python3

import argparse
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import struct
import cdi.files.module as module

parser = argparse.ArgumentParser(description='Display info about an OS-9 module file.')
parser.add_argument('filename', help='Module file to read', nargs='+')

args = parser.parse_args()

TYPES = {
         1: 'Program Module',
         2: 'Subroutine Module',
         3: 'Multi-Module (reserved for future use)',
         4: 'Data Module',
         5: 'Configuration Status Descriptor',
        11: 'User Trap Library',
        12: 'System Module (OS-9 component)',
        13: 'File Manager Module',
        14: 'Physical Device Driver',
        15: 'Device Descriptor Module'
    }

LANGS = {
        0: 'Unspecified Language (Wild Card value in system calls)',
        1: '68000 machine language',
        2: 'Basic I-code',
        3: 'Pascal P-code',
        4: 'C I-code (reserved for future use)',
        5: 'Cobol I-code',
        6: 'Fortran'
    }

class kv_table(object):
    def __init__(self, header):
        self.header = header
        self.rows = []

    def add_row(self, key, fmt, *args):
        if len(args) == 0:
            self.rows.append([ key, fmt ])
        else:
            self.rows.append([ key, fmt.format(*args) ])

    def add_table(self, table):
        assert isinstance(table, kv_table)
        self.rows.append(table)

    def print(self, indent=0):
        key_width    = 0
        value_width  = 0
        for row in self.rows:
            if not isinstance(row, kv_table):
                if len(row[0]) > key_width:
                    key_width = len(row[0])
                if len(row[1]) > value_width:
                    value_width = len(row[1])

        indent_str = ' ' * 4 * indent
        print(indent_str + self.header.center(key_width + 2 + value_width, '═'))
        for row in self.rows:
            if isinstance(row, kv_table):
                row.print(indent+1)
            else:
                print('{:s}{:s} {:s}'.format(indent_str, (row[0] + ':').ljust(key_width+1), row[1].ljust(value_width)))


def format_accs(accs):
    s = ''
    for whomst in reversed(range(4)):
        block = (accs >> (whomst*4)) & 0b1111
        s += 'r' if block & 0b0001 else '-'
        s += 'w' if block & 0b0010 else '-'
        s += 'x' if block & 0b0100 else '-'

    return s

for idx, filename in enumerate(args.filename):
    f = open(filename, 'rb')
    m = module.Module(f)

    if idx > 0:
        print()

    table = kv_table(filename)
    table.add_row('System revision', '{:d}', m.header.sysrev)
    table.add_row('Size of module', '{0:08X} ({0:d})', m.header.size)
    table.add_row('Owner ID', '{:d}', m.header.owner)
    table.add_row('Name', '{:08X} → {:s}', m.header.name, m.name)
    table.add_row('Access permissions', '{:12s} ({:04x})', format_accs(m.header.accs), m.header.accs)
    table.add_row('Type', '{:d} – {:s}', m.header.type, TYPES[m.header.type])
    table.add_row('Language', '{:2d} – {:s}', m.header.lang, LANGS[m.header.lang])
    table.add_row('Attributes', '{:08b}', m.header.attr)
    table.add_row('Revision level', '{:d}', m.header.revs)
    table.add_row('Edition', '{:d}', m.header.edit)

    if hasattr(m.header, 'exec'):
        table.add_row('Execution offset', '{:08X}', m.header.exec)

    if hasattr(m.header, 'excpt'):
        table.add_row('Default user trap execution entry point', '{:08X}', m.header.excpt)

    if hasattr(m.header, 'mem'):
        table.add_row('Memory size', '{0:08X} ({0:d})', m.header.mem)

    if hasattr(m.header, 'stack'):
        table.add_row('Stack size', '{0:08X} ({0:d})', m.header.stack)

    if hasattr(m.header, 'idata'):
        table.add_row('Initialized data offset', '{:08X}', m.header.idata)
        subtable = kv_table('Initialized data')
        subtable.add_row('Data offset', '{:08X}', m.idata.offset)
        subtable.add_row('Data size', '{0:08X} ({0:d}) bytes', m.idata.size)
        table.add_table(subtable)


    if hasattr(m.header, 'irefs'):
        table.add_row('Initialized references offset', '{:08X}', m.header.irefs)

        def resolve_data(offset):
            if offset >= m.idata.offset and offset < (m.idata.offset + m.idata.size):
                file_offset = m.header.idata + (offset - m.idata.offset)
                f.seek(file_offset)
                value, = struct.unpack('>I', f.read(4))

                return value
            else:
                return None

        def print_irefs(data, tag):
            n = len(data.refs)
            table = kv_table('{:s}: {:d} {:s}{:s}'.format(tag, n, 'entry' if n == 1 else 'entries', '' if n == 0 else ':'))

            for iref in data.refs:
                k = 'data:{:08X}'.format(iref)
                ptr = resolve_data(iref)
                if ptr is None:
                    v = ' (NOT IN IDATA)'
                else:
                    v = ' (= idata:{:08X} = file:{:08X} := {:s}:{:08X})'.format(iref - m.idata.offset, m.header.idata + (iref - m.idata.offset), tag, ptr)

                table.add_row(k, v)

            return table

        table.add_table(print_irefs(m.irefs.code, 'code'))
        table.add_table(print_irefs(m.irefs.data, 'data'))

    if m.header.type == module.ModuleHeader.TYPE_DEVIC:
        def read_string(f, offset):
            old_offset = f.tell()
            f.seek(offset)
            s = ''
            while True:
                b = f.read(1)
                if b == b'\x00':
                    break
                s += b.decode('ascii')

            f.seek(old_offset)
            return s

        f.seek(m.offset + 0x30)
        subtable = kv_table('Device descriptor')
        subtable.add_row('Port Address', '{:08X}', *struct.unpack('>I', f.read(4)))
        subtable.add_row('Trap Vector Number', '{:02X}', *struct.unpack('>B', f.read(1)))
        subtable.add_row('IRQ Interrupt Level', '{:02X}', *struct.unpack('>B', f.read(1)))
        subtable.add_row('IRQ Polling Priority', '{:02X}', *struct.unpack('>B', f.read(1)))
        subtable.add_row('Device Mode Capabilities', '{:02X}', *struct.unpack('>B', f.read(1)))
        fm_name_offset, = struct.unpack('>H', f.read(2))
        fm_name = read_string(f, m.offset + fm_name_offset)
        subtable.add_row('File Manager Name Offset', '{:04X} → {:s}', fm_name_offset, fm_name)
        dd_name_offset, = struct.unpack('>H', f.read(2))
        dd_name = read_string(f, m.offset + dd_name_offset)
        subtable.add_row('Device Driver Name Offset', '{:04X} → {:s}', dd_name_offset, dd_name)
        subtable.add_row('Device Configuration Offset', '{:04X}', *struct.unpack('>H', f.read(2)))
        f.read(8)
        subtable.add_row('Initialization Table Size', '{:04X}', *struct.unpack('>H', f.read(2)))
        subtable.add_row('Device Type', '{:02X}', *struct.unpack('>B', f.read(1)))

        table.add_table(subtable)

    table.print()
