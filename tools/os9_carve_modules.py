#!/usr/bin/env python3

import argparse
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import struct
import cdi.files.module as module

parser = argparse.ArgumentParser(description='Parse all valid OS-9 modules from a file (e.g. a ROM image) and write them to separate files.')
parser.add_argument('filename', help='Image file to read')

args = parser.parse_args()

matched = 0

with open(args.filename, 'rb') as f:
    while True:
        b = f.read(1)
        if len(b) != 1:
            break

        if matched == 0:
            if b == b'\x4A':
                matched = 1
            else:
                matched = 0
        elif matched == 1:
            matched = 0
            if b == b'\xFC':
                print('Possible match @ {:08x}'.format(f.tell() - 2))
                start = f.tell() - 2

                try:
                    module = module.Module(f, start)

                    print('\tModule name: {:s}'.format(module.name))

                    with open(module.name, 'wb') as outf:
                        outf.write(module.get_data())

                    f.seek(module.offset + module.header.size)

                except RuntimeError:
                    f.seek(start + 2)
                    continue
