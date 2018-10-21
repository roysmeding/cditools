#!/usr/bin/env python3

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import argparse
import struct
from cdi.files.font import FontModule

parser = argparse.ArgumentParser(description='Extract a font to a file')
parser.add_argument('infile', help='Font file to read')
parser.add_argument('outfile', help='PGM to write to')
parser.add_argument('--full-bitmap', '-b', action='store_true', help='Extract full bitmap instead of series of characters')
parser.add_argument('--msg', '-m', help='The message to render')

args = parser.parse_args()

if (not args.msg is None) and args.full_bitmap:
    print('Cannot both dump the full bitmap and render a message at the same time.')
    sys.exit(1)

FONT_TYPES = {
        FontModule.TYPE_SINGLE_BIT: 'Single-bit',
        FontModule.TYPE_DOUBLE_BIT: 'Double-bit',
        FontModule.TYPE_QUAD_BIT:   'Quad-bit',
        FontModule.TYPE_CLUT4:      'CLUT4',
        FontModule.TYPE_CLUT7:      'CLUT7',
        FontModule.TYPE_CLUT8:      'CLUT8',
        FontModule.TYPE_RGB555:     'RGB555',
    }

with open(args.infile, 'rb') as f:
    fnt = FontModule(f)

if fnt.proportional:
    print('Proportional font')

if fnt.monospace:
    print('Monospace font')

try:
    print('Font data type: {:s}'.format(FONT_TYPES[fnt.data_type]))
except KeyError:
    print('Unknown font data type 0x{:X}'.format(fnt.data_type))
    

print("""
Maximum glyph cell width:                 {0:3d} px
Glyph cell height (ascent + descent):     {1:3d} px
Ascent of character cell above baseline:  {2:3d} px
Descent of character cell below baseline: {3:3d} px

Pixel size: {4:d} bits
First character value of font: {5:04X} ({5:c})
Last character value of font:  {6:04X} ({6:c})

Line length of first font bitmap:   {7:08X} ({7:d}) bytes
Offset to glyph offset table:       {8:08X} ({8:d})
Offset to glyph data table:         {9:08X} ({9:d})
Offset to first bitmap:             {10:08X} ({10:d})
Offset to second bitmap (RGB only): {11:08X} ({11:d})
""".format(fnt.width, fnt.height, fnt.ascent, fnt.descent, fnt.pxlsz, fnt.frstch, fnt.lastch, fnt.lnlen, fnt.offstbl, fnt.databl, fnt.map1off, fnt.map2off)
)

if os.path.isdir(args.outfile):
    outfile = os.path.join(args.outfile, os.path.basename(args.infile) + '.pgm')
else:
    outfile = args.outfile
    if not outfile.endswith('.pgm'):
        outfile += '.pgm'

with open(outfile, 'wb') as outf:
    if args.full_bitmap:
        outf.write('P2\n{:d} {:d}\n{:d}\n'.format(fnt.lnlen*8, fnt.height, (1 << fnt.pxlsz) - 1).encode('ascii'))

        for y in range(fnt.height):
            for x in range(fnt.lnlen*8):
                pixel = fnt.get_pixel(x, y)
                outf.write('{:d} '.format(pixel).encode('ascii'))

            outf.write(b'\n')
    else:
        if args.msg is None:
            msg = ''.join(chr(v) for v in fnt.offsets.keys())
            total_width = fnt.total_width
        else:
            msg = args.msg
            total_width = sum(fnt.widths[ord(ch)] for ch in msg)


        outf.write('P2\n{:d} {:d}\n{:d}\n'.format(total_width, fnt.height, (1 << fnt.pxlsz) - 1).encode('ascii'))

        for y in range(fnt.height):
            for ch in msg:
                offset = fnt.offsets[ord(ch)]
                for x in range(fnt.widths[ord(ch)]):
                    pixel = fnt.get_pixel(offset+x, y)
                    outf.write('{:d} '.format(pixel).encode('ascii'))

            outf.write(b'\n')
