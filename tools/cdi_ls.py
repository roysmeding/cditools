import argparse
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import cdi

# parse command-line arguments
parser = argparse.ArgumentParser(description='List all directories, files, records and channels from a CD-I disc image')
parser.add_argument('image_file',  help='Image file to list')
parser.add_argument('--headers', '-H', action='store_true', help='Image file has CD headers')
parser.add_argument('--simple',  '-s', action='store_true', help='Simple view without fancy directory tree')
parser.add_argument('--records', '-R', action='store_true', help='Display information about each record in a real-time file')

args = parser.parse_args()

img = cdi.Image(args.image_file, headers=args.headers)

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
    for block in f.get_blocks():
        if block.subheader.realtime and flags[0] != 'r':
            flags =             'r' + flags[1:]

        if block.subheader.video and flags[1] != 'v':
            flags = flags[:1] + 'v' + flags[2:]

        if block.subheader.audio and flags[2] != 'a':
            flags = flags[:2] + 'a' + flags[3:]

        if block.subheader.data and flags[3] != 'd':
            flags = flags[:3] + 'd'

    return flags

MAX_DEPTH = 5

def print_records(f, depth, last_file):
    record_idx = 0
    flags = '-'*4
    size = 0

    for block in f.get_blocks():
        if block.subheader.realtime and flags[0] != 'r':
            flags =             'r' + flags[1:]

        if block.subheader.video and flags[1] != 'v':
            flags = flags[:1] + 'v' + flags[2:]

        if block.subheader.audio and flags[2] != 'a':
            flags = flags[:2] + 'a' + flags[3:]

        if block.subheader.data and flags[3] != 'd':
            flags = flags[:3] + 'd'

        size += block.data_size
        if block.subheader.eor or block.subheader.eof:
            last_record = (record_idx == len(f.records) - 1)

            sys.stdout.write(" "*48)

            sys.stdout.write(" ┃"*depth)
            sys.stdout.write("   " if last_file else " ┃ ")

            sys.stdout.write("└" if last_record else "├")
            sys.stdout.write("─●")

            sys.stdout.write("  "*(MAX_DEPTH - depth - 1))

            sys.stdout.write("{:10d}  {:4s}    record {:d}\n".format(size, flags, record_idx))

            record_idx += 1
            flags = '-'*4
            size = 0


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
        sys.stdout.write(" ┃"*depth)
        
        if depth == 0 and first:
            sys.stdout.write(" ┳")
        elif last:
            sys.stdout.write(" ┗")
        else:
            sys.stdout.write(" ┣")

        if f.is_directory:
            sys.stdout.write("━◇")
            sys.stdout.write("  "*(MAX_DEPTH - depth))
            sys.stdout.write("{:10d}        \033[1m{:28s}\033[0m\n".format(f.size, f.name))

            print_dir(f.directory_record, depth+1)

            sys.stdout.write(" "*48)
            sys.stdout.write(" ┃"*(depth+1))
            sys.stdout.write("\n")

        else:
            if len(f.records) == 1:
                sys.stdout.write("━■")
                sys.stdout.write("  "*(MAX_DEPTH - depth))
                sys.stdout.write("{:10d}  {:4s}  {:28s}\n".format(
                        f.size,
                        get_flags(f),
                        f.name
                    ))

            else:
                sys.stdout.write("━□")
                sys.stdout.write("  "*(MAX_DEPTH - depth))

                if args.records:
                    sys.stdout.write("{:10d}  {:4s}  {:28s}\n".format(
                            f.size,
                            get_flags(f),
                            f.name
                        ))

                    print_records(f, depth, last)

                    if not last:
                        sys.stdout.write(" "*48)
                        sys.stdout.write(" ┃"*(depth+1))
                        sys.stdout.write("\n")
                else:
                    sys.stdout.write("{:10d}  {:4s}  {:28s}  ({:d} records)\n".format(
                            f.size,
                            get_flags(f),
                            f.name,
                            len(f.records)
                        ))


print_dir(img.root)
