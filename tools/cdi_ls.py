#!/usr/bin/env python3

import argparse
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import cdi

# parse command-line arguments
parser = argparse.ArgumentParser(description='List all directories and files from a CD-I disc image')
parser.add_argument('discfile', help='Disc image file to decode from')
parser.add_argument('--no-cd-headers', '-H', dest='headers', action='store_false', help='Image file does not have CD headers')

args = parser.parse_args()

img = cdi.Image(args.discfile, headers=args.headers)

ATTR_FILL = "-"

def format_attributes(attr):
    s = ''
    if attr.cdda:
        s += 'c'
    elif attr.directory:
        s += 'd'
    else:
        s += ATTR_FILL

    s += 'r' if attr.owner_read else ATTR_FILL
    s += ATTR_FILL
    s += 'x' if attr.owner_exec else ATTR_FILL
    
    s += 'r' if attr.group_read else ATTR_FILL
    s += ATTR_FILL
    s += 'x' if attr.group_exec else ATTR_FILL
    
    s += 'r' if attr.world_read else ATTR_FILL
    s += ATTR_FILL
    s += 'x' if attr.world_exec else ATTR_FILL

    return s

def get_flags(f):
    flags = '-'*4
    for block in f.blocks():
        if block.subheader.realtime and flags[0] != 'r':
            flags =             'r' + flags[1:]

        if block.subheader.video and flags[1] != 'v':
            flags = flags[:1] + 'v' + flags[2:]

        if block.subheader.audio and flags[2] != 'a':
            flags = flags[:2] + 'a' + flags[3:]

        if block.subheader.data and flags[3] != 'd':
            flags = flags[:3] + 'd'

    return flags

def print_dir(d, depth=0, root=True):
    for i, f in enumerate(d.contents):
        first = (i == 0)
        last = (i == len(d.contents)-1)

        # general per-file metadata
        sys.stdout.write(
                "{:10s}  {:5d}  {:5d}  {:20s}  ".format(
                    format_attributes(f.attributes),
                    f.owner_group,
                    f.owner_user,
                    f.creation_date.strftime('%b %d %Y %H:%M:%S')
                )
            )

        # tree view
        if f.is_directory:
            sys.stdout.write("{:10d}        {:28s}\n".format(f.size, f.full_name))

            print_dir(f.directory_record, depth+1)

            sys.stdout.write("\n")

        else:
            sys.stdout.write("{:10d}  {:4s}  {:28s}\n".format(
                    f.size,
                    get_flags(f),
                    f.full_name
                ))

print_dir(img.root)
