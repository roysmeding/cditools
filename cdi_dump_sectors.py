from cdi import *
import argparse
import sys

# parse command-line arguments
parser = argparse.ArgumentParser(description='Dump information about a CD-I disc image')
parser.add_argument('image_file',   help='Image file to dump')
parser.add_argument('sector_spec',  help='Sectors to export')
parser.add_argument('output_file',  help='Output file name')

parser.add_argument('-c', '--channel', type=int, default=None, help='Export only the specified channel')
parser.add_argument('-a', '--audio', action='store_true', help='Export audio sectors')
parser.add_argument('-v', '--video', action='store_true', help='Export video sectors')
parser.add_argument('-d', '--data',  action='store_true', help='Export data sectors')
parser.add_argument('-e', '--empty', action='store_true', help='Export empty sectors')
args = parser.parse_args()

with open(args.image_file, 'rb') as cdifile:
    disc = Disc(cdifile)
    disc.read()

    sectors = args.sector_spec.split('-')
    if len(sectors) > 2:
        print "barf"
        sys.exit(2)

    if len(sectors) == 1:
        sector_list = [int(sectors[0])]
    else:
        sector_list = range(int(sectors[0]), int(sectors[1]))

    with open(args.output_file, 'wb') as outfile:
        for sector in sector_list:
            if args.channel == None or args.channel == sector.subheader.channel_number:
                if (disc[sector].subheader.data  and args.data) or (disc[sector].subheader.audio and args.audio) or (disc[sector].subheader.video and args.video) or (disc[sector].subheader.empty and args.empty):
                    outfile.write(disc[sector][:])
