#!/usr/bin/env python3

import sys

import argparse
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import cdi

from cdi.sector import VideoCoding, AudioCoding

# ANSI escape codes
RESET = "\033[0m"

RED   = "\033[0;41;97m"
GREEN = "\033[0;42;97m"
BLUE  = "\033[0;44;97m"

BOLD      = "\033[1m"
UNDERLINE = "\033[4m"


VIDEO_ENCODINGS = ['CLUT4', 'CLUT7', 'CLUT8', 'RL3', 'RL7', 'DYUV', 'RGB555L', 'RGB555U', 'QHY']
HEADERS=['address', 'sector', 'file', 'channel', 'type', 'filename', 'fileidx', 'record', 'encoding', 'form', 'trig', 'realtime', 'EOR', 'EOF']

# parse command-line arguments
parser = argparse.ArgumentParser(description='Dump sector information from a CD-I disc image')
parser.add_argument('image_file', help='Image file to dump')
parser.add_argument('--raw', '-r', action='store_true', help='Read raw image file (do not attempt to parse disc labels, path tables, etc.). Useful for partial, corrupted or non-standard disc images.')
args = parser.parse_args()

col_widths = [len(h) for h in HEADERS]
record_index = 0

if args.raw:
    img = cdi.RawImage(args.image_file)
    files_by_block = None

else:
    try:
        img = cdi.Image(args.image_file)

        files_by_block = {}
        for d in img.path_table.directories:
            for f in d.contents:
                files_by_block[f.first_block.index] = f

    except Exception as e:
        sys.stderr.write('Failed to read path table. Using the --raw option might help.\n')
        raise e

table = []
current_files = {}
file_bytes    = {}
for sector in img.get_sectors():
    row = {}
    row['address'] = "%08X" % sector.data_offset
    row['sector']  = "%06d" % sector.index

    h = sector.subheader
    row['file']    = "%02d" % h.file_number
    row['channel'] = "%02d" % h.channel_number

    if not files_by_block is None:
        if sector.index in files_by_block:
            f = files_by_block[sector.index]
            current_files[f.number] = f
            file_bytes[f.number]    = 0
            record_index = 0

    if h.file_number in current_files:
        current_idx = h.file_number
    else:
        current_idx = 0

    try:
        row['filename'] = repr(current_files[current_idx].name)
        row['fileidx']  = "%8d" % file_bytes[current_idx]
    except KeyError:
        row['filename'] = ""
        row['fileidx']  = "-"*8

    if h.video:
        row['type'] = "V"

        if h.coding is None:
            row['encoding'] = "app-specific 0x{:02X}".format(h.coding_raw)

        elif h.coding.encoding == VideoCoding.ENCODING_MPEG:
            row['encoding'] = "MPEG"

        else:
            try:                row['encoding'] = VIDEO_ENCODINGS[h.coding.encoding]
            except IndexError:  row['encoding'] = "<reserved encoding 0x{:01X}>".format(h.coding.encoding)

            if h.coding.odd_lines:       row['encoding'] += ", odd lines"
            else:                        row['encoding'] += ", even lines"

            if   h.coding.resolution == VideoCoding.RESOLUTION_HIGH:
                row['encoding'] += ", high res"

            elif h.coding.resolution == VideoCoding.RESOLUTION_DOUBLE:
                row['encoding'] += ", double res"

            elif h.coding.resolution == VideoCoding.RESOLUTION_NORMAL:
                row['encoding'] += ", normal res"

            else:
                row['encoding'] += ", <reserved res>"

    if h.audio:
        row['type'] = "A"

        if h.coding_raw == 0b01111111:
            row['encoding'] = "MPEG"

        else:
            if   h.coding.sample_rate == AudioCoding.SAMPLE_RATE_18900:
                row['encoding']  = "18.9kHz"
            elif h.coding.sample_rate == AudioCoding.SAMPLE_RATE_37800:
                row['encoding']  = "37.8kHz"
            else:
                row['encoding']  = "<reserved rate {:01d}>".format(h.coding.sample_rate)

            if   h.coding.sample_depth == AudioCoding.SAMPLE_DEPTH_8BIT:
                row['encoding'] += ", 8bit"
            else:
                row['encoding'] += ", 4bit"

            if   h.coding.emphasis:
                row['encoding'] += ", emphasis, "
            else: 
                row['encoding'] += ",           "

            if   h.coding.stereo:
                row['encoding'] += "stereo"

            elif h.coding.mono:
                row['encoding'] += "mono  "

            else:
                row['encoding'] += "<reserved channel number <{:01d}>".format(h.coding.layout)

    if h.data:      row['type'] = "D"
    if h.empty:     row['type'] = "E"

    if h.form1:     row['form'] = "1"
    else:           row['form'] = "2"

    if h.trigger:   row['trig'] = "T"

    if h.realtime:  row['realtime'] = "RT"

    if h.eor:       row['EOR'] = "EOR"
    if h.eof:       row['EOF'] = "EOF"

    row['record'] = "%d" % record_index

    if h.eor:       record_index += 1
    if h.eof:       record_index  = 0

    try:
        file_bytes[current_idx] += 2048
        if h.eof or (file_bytes[current_idx] >= current_files[current_idx].size):
            del current_files[current_idx]
            del file_bytes[current_idx]
    except KeyError:
        pass

    r = []
    for i, key in enumerate(HEADERS):
        try:
            r.append(row[key])
            col_widths[i] = max(col_widths[i], len(row[key]))
        except KeyError:
            r.append("")
    table.append(r)

for i in range(len(col_widths)):
    col_widths[i] += 2

# make fancy table
sys.stdout.write(BOLD)
sys.stdout.write(UNDERLINE)
for i, col in enumerate(HEADERS):
    padding = col_widths[i] - len(col)
    if padding%2 == 0:
        pad_left  = int(padding/2)
        pad_right = int(padding/2)
    else:
        pad_left  = int(padding/2)
        pad_right = int(padding/2)+1
    sys.stdout.write(" "*pad_left + col + " "*pad_right)
sys.stdout.write(RESET+"\n")

for row in table:
    if row[4] == 'D':
        sys.stdout.write(BLUE)
    elif row[4] == 'A':
        sys.stdout.write(GREEN)
    elif row[4] == 'V':
        sys.stdout.write(RED)

    if row[-1] != "" or row[-2] != "":
        sys.stdout.write(UNDERLINE)

    if row[-4] != "":
        sys.stdout.write(BOLD)

    for i, cell in enumerate(row):
        padding = col_widths[i] - len(cell)
        if padding%2 == 0:
            pad_left  = int(padding/2)
            pad_right = int(padding/2)
        else:
            pad_left  = int(padding/2)
            pad_right = int(padding/2)+1
        sys.stdout.write(" "*pad_left + cell + " "*pad_right)
    sys.stdout.write(RESET + "\n")
