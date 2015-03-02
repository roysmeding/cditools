from cdi import *
import argparse
import numpy as np

# parse command-line arguments
parser = argparse.ArgumentParser(description='Decode DYUV image data from an extracted CD-I video track')
parser.add_argument('input_file',   help='Track file to decode')
parser.add_argument('output_base',  help='Output file name base')

args = parser.parse_args()

# initialize
infile  = open(args.input_file, 'rb')   # input file
indisc  = Disc(infile)                  # input Disc object (not a full disc image)

WIDTH = 384
HEIGHT = 240

y = 0
x = 0

delta_y = []
delta_u = []
delta_v = []

offset = 0
while offset < indisc.image_file.size():
    sector = Sector(indisc, offset)

    sh = sector.subheader
    if not sh.video:
        offset = sector.offset + Sector.FULL_SIZE
        continue
    #assert sh.video, "Found non-video sector in file"

    i = 0
    while i < sector.data_size:
        b1, b2 = ord(sector.data[i]), ord(sector.data[i+1])
        delta_u.append((b1 & 0xf0) >> 4)
        delta_y.append( b1 & 0x0f )
        delta_v.append((b2 & 0xf0) >> 4)
        delta_y.append( b2 & 0x0f )

        x += 2
        i += 2
        if x >= WIDTH:
            x  = 0
            y += 1
            if y >= HEIGHT:
                break

    offset = sector.offset + Sector.FULL_SIZE

# delta decoding and interpolation
y_initial, u_initial, v_initial = 0, 128, 0

quant = [ 0, 1, 4, 9, 16, 27, 44, 79, 128, 177, 212, 229, 240, 247, 252, 255 ]

print "Read %d bytes." % len(delta_y)

for idx in xrange(len(delta_y)//(WIDTH*HEIGHT)):
    print "Image #%d" % idx
    img = open("%s_%04d.pnm" % (args.output_base, idx), 'w')
    img.write("P3\n")                          
    img.write("%d %d\n" % (WIDTH, HEIGHT))     
    img.write("255\n")                         

    start = WIDTH*HEIGHT*idx
    end   = WIDTH*HEIGHT*(idx+1)
    lum     = np.reshape(np.array(delta_y[start:end]), (HEIGHT, WIDTH  ), order='C')
    chrom_u = np.reshape(np.array(delta_u[start//2:end//2]), (HEIGHT, WIDTH//2), order='C')
    chrom_v = np.reshape(np.array(delta_v[start//2:end//2]), (HEIGHT, WIDTH//2), order='C')

    for y in xrange(HEIGHT):
        y_pred, u_pred, v_pred = y_initial, u_initial, v_initial
        for x in xrange(WIDTH):
            output_y = (y_pred + quant[lum[y][x]]) % 256
            y_pred = output_y

            if x%2 == 0 or x > (WIDTH-2):
                output_u = (u_pred + quant[chrom_u[y][x//2]]) % 256
                u_pred = output_u

                output_v = (v_pred + quant[chrom_v[y][x//2]]) % 256
                v_pred = output_v
            else:
                output_u = (u_pred + quant[chrom_u[y][x//2 + 1]/2]) % 256    # interpolated u
                output_v = (v_pred + quant[chrom_v[y][x//2 + 1]/2]) % 256    # interpolated v

            # matrixing to get RGB
            B = output_y + (output_u - 128) * 1.733
            R = output_y + (output_v - 128) * 1.371
            G = (output_y - 0.299 * R - 0.114 * B) / 0.587

            img.write("%3d %3d %3d " % (int(R), int(G), int(B)))
        img.write("\n")
