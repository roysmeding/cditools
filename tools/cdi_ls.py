#!/usr/bin/env python3

import argparse
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import cdi

# parse command-line arguments
parser = argparse.ArgumentParser(description='List all directories and files from a CD-I disc image')
parser.add_argument('discfile', help='Disc image file to decode from')
parser.add_argument('--realtime', action='store_true', help='Only list realtime files')
parser.add_argument('--plain', action='store_true', help='List only file names, separated by newlines.')

args = parser.parse_args()

img = cdi.Image(args.discfile)

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
    for f in d.contents:

        # general per-file metadata
        if f.is_directory:
            if args.plain or args.realtime:
                print_dir(f.directory_record, depth+1)
            else:
                sys.stdout.write(
                        '{:10s}  {:5d}  {:5d}  {:20s}  {:10d}        {:28s}\n'.format(
                            format_attributes(f.attributes),
                            f.owner_group,
                            f.owner_user,
                            f.creation_date.strftime('%b %d %Y %H:%M:%S'),
                            f.size,
                            f.full_name
                        )
                    )

                print_dir(f.directory_record, depth+1)
                sys.stdout.write('\n')

        else:
            file_flags = get_flags(f)

            if args.realtime and file_flags[0] != 'r':
                continue

            if args.plain:
                sys.stdout.write('{:s}\n'.format(f.full_name))
                
            else:
                sys.stdout.write(
                        '{:10s}  {:5d}  {:5d}  {:20s}  {:10d}  {:4s}  {:28s}\n'.format(
                            format_attributes(f.attributes),
                            f.owner_group,
                            f.owner_user,
                            f.creation_date.strftime('%b %d %Y %H:%M:%S'),
                            f.size,
                            file_flags,
                            f.full_name
                        )
                    )

print_dir(img.root)