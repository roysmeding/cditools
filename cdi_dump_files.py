from cdi import *
import argparse
import sys

# parse command-line arguments
parser = argparse.ArgumentParser(description='Dumps all directories, files, records and channels from a CD-I disc image')
parser.add_argument('image_file',  help='Image file to dump')
parser.add_argument('output_dir',  help='Directory to write to')
parser.add_argument('--headers', '-H', action='store_true', help='Image file includes CD headers')

args = parser.parse_args()

with open(args.image_file, 'rb') as cdifile:
    disc = Disc(cdifile, args.headers)
    disc.read()

    for directory in disc.path_tbl:
        # print path name
        path = '/'
        d = directory
        while d.parent != 1:
            path = '/' + d.name + path
            d = disc.path_tbl[d.parent]

        for file in directory:
            if not file.attributes.directory:
                lbn  = file.first_lbn
                byte = 0
                channels = {}
                record_num = 0
                while True:
                    block = disc.block(lbn)
                    sh = block.subheader
                    if not sh.channel_number in channels:
                        channels[sh.channel_number] = open('%s%s%s.r%04dch%02d' % (args.output_dir, path, file.name, record_num, sh.channel_number), 'wb')

                    channels[sh.channel_number].write(block[:])

                    byte += block.data_size
                    lbn  += 1

                    if block.subheader.eor or block.subheader.eof:
                        print "%-20s record %4d channel %2d" % (path+file.name, record_num, sh.channel_number)

                        channels[sh.channel_number].close()
                        del channels[sh.channel_number]
                        record_num += 1

                    if block.subheader.eof:
                        for v in channels.keys():
                            channels[v].close()
                            del channels[v]
                        break
            print
