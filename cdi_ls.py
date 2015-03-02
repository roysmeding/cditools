from cdi import *
import argparse
import sys

# parse command-line arguments
parser = argparse.ArgumentParser(description='List all directories, files, records and channels from a CD-I disc image')
parser.add_argument('image_file',  help='Image file to list')

args = parser.parse_args()

with open(args.image_file, 'rb') as cdifile:
    disc = Disc(cdifile)
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
                        channels[sh.channel_number] = [0]*4

                    if sh.empty: channels[sh.channel_number][0] += 1
                    if sh.data:  channels[sh.channel_number][1] += 1
                    if sh.audio: channels[sh.channel_number][2] += 1
                    if sh.video: channels[sh.channel_number][3] += 1

                    byte += block.data_size
                    lbn += 1

                    if block.subheader.eor or block.subheader.eof or byte >= file.size:
                        for channel, contents in channels.items():
                            print "%-20s record %4d channel %2d:" % (path+file.name, record_num, channel),
                            if contents[0] > 0: print "%4d empty" % contents[0],
                            else:               print "          ",
                            if contents[1] > 0: print "%4d data " % contents[1],
                            else:               print "          ",
                            if contents[2] > 0: print "%4d audio" % contents[2],
                            else:               print "          ",
                            if contents[3] > 0: print "%4d video" % contents[3]
                            else:               print "          "

                        if len(channels) > 1:
                            print
                        channels = {}
                        record_num += 1

                    if block.subheader.eof or byte >= file.size:
                        break
                if record_num > 1:
                    print
            print
