import argparse
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import cdi

# parse command-line arguments
parser = argparse.ArgumentParser(description='Extracts files from a CD-I disc image')
parser.add_argument('image_file', help='Image file to extract')
parser.add_argument('output_dir', help='Directory to extract to')
parser.add_argument('--headers', '-H', action='store_true', help='Image file has CD headers')
parser.add_argument('--records', '-R', action='store_true', help='Extract file records / channels as separate files')

args = parser.parse_args()

img = cdi.Image(args.image_file, headers=args.headers)

def cdi2native(path):
    return os.path.join(args.output_dir, *path.split('/'))

RECORD_FILE_PATTERN = "{:s}.r{:06d}.ch{:02d}"

for d in img.path_table.directories:
    outdir = cdi2native(d.full_name)
    print(outdir)
    os.makedirs(outdir)
    for f in d.contents:
        outfile = cdi2native(f.full_name)

        if f.is_directory:
            continue

        if args.records and (len(f.records) > 1):
            print(outfile + os.sep)

            os.makedirs(outfile)

            for record_idx, record_info in enumerate(f.records):
                for channel_idx in record_info.channels.keys():
                    outfname = os.path.join(outfile, RECORD_FILE_PATTERN.format(f.name, record_idx, channel_idx))
                    print(outfname)

                    ifs = f.open(record_idx, channel_idx)
                    with open(outfname, 'wb') as outf:
                        while not ifs.eof:
                            outf.write(ifs.read_block())

        else:
            print(outfile)
            ifs = f.open()

            with open(outfile, 'wb') as outf:
                while not ifs.eof:
                    outf.write(ifs.read_block())
