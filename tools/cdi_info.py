#!/usr/bin/env python3

import argparse
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import cdi

# color stuff
BOLD = '\033[1m'
ENDC = '\033[0m'

# parse command-line arguments
parser = argparse.ArgumentParser(description='Lists information about a CD-I disc image.')
parser.add_argument('image_file',  help='Image file to open')
parser.add_argument('--headers', '-H', action='store_true', help='Image file has CD headers')

args = parser.parse_args()
img = cdi.Image(args.image_file, headers=args.headers)

for idx, dl in enumerate(img.disc_labels):
    print((BOLD+"Disc label"+ENDC+" #{:d}: \"{:s}\"").format(idx, dl.volume_id))
    print(("\t"+BOLD+"Version"+ENDC+" {:d}, "+BOLD+"System Identifier"+ENDC+" \"{:s}\"").format(dl.version, dl.system_id))
    print(("\t"+BOLD+"Size"+ENDC+": {:d} blocks").format(dl.volume_size))
    print(("\t"+BOLD+"Album"+ENDC+": \"{:s}\" "+BOLD+"disc"+ENDC+" #{:d}/{:d}").format(dl.album_id, dl.album_idx, dl.album_size))
    print(("\t"+BOLD+"Publisher"+ENDC+": \"{:s}\"").format(dl.publisher_id))
    print(("\t"+BOLD+"Data Preparer"+ENDC+": \"{:s}\"").format(dl.data_preparer))


    # dates
    def fmtdate(date):
        if date is None:
            return "<none>"
        else:
            return date.strftime("%Y-%m-%d %H:%M:%S")

    print(("\t"+BOLD+"Created"+ENDC+":   {:19s}  "+BOLD+"Modified"+ENDC+": {:19s}").format(fmtdate(dl.created_date), fmtdate(dl.modified_date)))
    print(("\t"+BOLD+"Effective"+ENDC+": {:19s}  "+BOLD+"Expires"+ENDC+":  {:19s}").format(fmtdate(dl.effective_date), fmtdate(dl.expires_date)))

    print()


dl = img.disc_labels[0]

# special files
def get_file(filename):
    for f in img.root.contents:
        if f.name == filename:
            return f

    raise ValueError("File not found")

def _normalize_newlines(string):
    import re
    return re.sub(r'(\r\n|\r|\n)', '\n', string)

def print_file(header, filename):
    print(BOLD+header+ENDC)
    print(_normalize_newlines(get_file(filename).open().read().decode('iso-8859-1')))
    print()

print_file("Copyright file", dl.copyright_file)
print_file("Abstract file",  dl.abstract_file)
print_file("Bibliographic file", dl.biblio_file)

print((BOLD+"Application to start when mounted"+ENDC+": {:s}").format(dl.app_id))
