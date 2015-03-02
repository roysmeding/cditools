from cdi import *
import sys

import argparse

# ANSI escape codes
RESET = "\033[0m"

RED   = "\033[0;41;97m"
GREEN = "\033[0;42;97m"
BLUE  = "\033[0;44;97m"

BOLD      = "\033[1m"
UNDERLINE = "\033[4m"


VIDEO_CODINGS = ['CLUT4', 'CLUT7', 'CLUT8', 'RL3', 'RL7', 'DYUV', 'RGB555L', 'RGB555U', 'QHY']
HEADERS=['address', 'sector', 'block', 'file', 'channel', 'type', 'filename', 'fileidx', 'record', 'encoding', 'form', 'trig', 'realtime', 'EOR', 'EOF']

# parse command-line arguments
parser = argparse.ArgumentParser(description='Dump information about a CD-I disc image')
parser.add_argument('image_file', help='Image file to dump')
parser.add_argument('--headers', '-H', action='store_true', help='Image file has CD headers')
parser.add_argument('--raw', '-R', action='store_true', help='Image file does not have full file system')
args = parser.parse_args()

col_widths = [len(h) for h in HEADERS]
record_index = 0
with open(args.image_file, 'rb') as cdifile:
    disc = Disc(cdifile, headers=args.headers)
    if args.raw:
        disc.read_sectors()
    else:
        disc.read()

    table = []
    current_files = {}
    file_bytes    = {}
    for sector_index, sector in enumerate(disc):
        row = {}
        row['address'] = "%08X" % sector.offset
        row['sector']  = "%06d" % sector_index
        if args.raw:
            row['block'] = '-'*6
        else:
            row['block']   = "%06d" % disc.sector2lbn(sector_index)

        h = sector.subheader
        row['file']    = "%02d" % h.file_number
        row['channel'] = "%02d" % h.channel_number

        if not args.raw:
            for d in disc.path_tbl:
                for f in d:
                    if f.first_lbn == disc.sector2lbn(sector_index):
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

            if h.coding_raw == 0b00001111:
                row['encoding'] = "MPEG"
            else:
                if h.coding_raw & (1<<7):
                    row['encoding'] = "app-specific"
                else:
                    try:                row['encoding'] = VIDEO_CODINGS[h.coding_raw & 0b00001111]
                    except IndexError:  row['encoding'] = "<reserved>"

                    if h.coding_raw & (1<<6):       row['encoding'] += ", odd lines"
                    else:                           row['encoding'] += ", even lines"

                    if h.coding_raw & (1<<5):
                        if h.coding_raw & (1<<4):   row['encoding'] += ", high res"
                    else:
                        if h.coding_raw & (1<<4):   row['encoding'] += ", double res"
                        else:                       row['encoding'] += ", normal res"

        if h.audio:
            row['type'] = "A"
            if h.coding_raw == 0b01111111:
                row['encoding'] = "MPEG"
            else:
                if h.coding_raw & (1<<2):   row['encoding']  = "18.9kHz"
                else:                       row['encoding']  = "37.8kHz"

                if h.coding_raw & (1<<4):   row['encoding'] += ", 8bit"
                else:                       row['encoding'] += ", 4bit"

                if h.coding_raw & (1<<6):   row['encoding'] += ", emphasis, "
                else:                       row['encoding'] += ",           "

                if h.coding_raw & (1<<0):   row['encoding'] += "stereo"
                else:                       row['encoding'] += "mono"

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
        if row[5] == 'D':
            sys.stdout.write(BLUE)
        elif row[5] == 'A':
            sys.stdout.write(GREEN)
        elif row[5] == 'V':
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
