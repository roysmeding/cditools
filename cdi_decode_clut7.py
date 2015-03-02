from cdi import *
import argparse

# parse command-line arguments
parser = argparse.ArgumentParser(description='Decode CLUT7 image data from an extracted CD-I video track')
parser.add_argument('input_file',   help='Track file to decode')
parser.add_argument('--offset',     help='Offset into the file that the image starts at', type=int, default=0)
parser.add_argument('-i', '--ignore-other', help='Ignore non-video data in file', action="store_true")
parser.add_argument('--clut', '-l', help='Colour lookup table file', type=str, default=None)
parser.add_argument('output_base',  help='Output file name base')

args = parser.parse_args()

# initialize
infile  = open(args.input_file, 'rb')   # input file
indisc  = Disc(infile)                  # input Disc object (not a full disc image)

WIDTH = 384
HEIGHT = 240

def open_pnm(file_index):
    global args, WIDTH, HEIGHT
    f = open("%s%04d.pnm"%(args.output_base, file_index), 'w')
    f.write("P3\n")
    f.write("%d %d\n" % (WIDTH, HEIGHT))
    f.write("255\n")
    return f

# open CLUT
if args.clut is None:
    clut = ["%d %d %d" % () for i in range(128)]
else:
    clut = []
    with open(args.clut) as cf:
        for l in cf.readlines():
            v = l.strip().split()
            col = " ".join((str(int(comp, 16)) for comp in v[1:]))
            clut.append(col)

file_index = 0
outfile = None

y = 0
x = 0

num_pixels = 0
offset = args.offset
while offset < indisc.image_file.size():
    sector = Sector(indisc, offset)

    sh = sector.subheader
    if args.ignore_other:
        if (not sh.video) or sh.coding_raw != 0b00000001:
            offset += sector.FULL_SIZE
            continue
    else:
        assert sh.video, "Found non-video sector in file"

    i = 0
    while i < sector.data_size:
        if outfile is None:
            print "%s%04d.pnm:"%(args.output_base, file_index),
            outfile = open_pnm(file_index)
            num_pixels = 0

        b = ord(sector.data[i])

        num_pixels += 1
        outfile.write(clut[b] + " ")

        x += 1
        i += 1
        if x >= WIDTH:
            outfile.write("\n")
            x  = 0
            y += 1
            if y >= HEIGHT:
                y = 0
                file_index += 1
                print "%d pixels written." % num_pixels
                outfile.close()
                outfile = None

    offset += sector.FULL_SIZE

if not (outfile is None):
    print "%d pixels written." % num_pixels
    outfile.close()

