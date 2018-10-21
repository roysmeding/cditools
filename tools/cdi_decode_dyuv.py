#!/usr/bin/env python3

import argparse
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import cdi
import cdi.formats.dyuv
from decoders.sequencer import Sequencer

# parse command-line arguments
parser = argparse.ArgumentParser(
        description='Decodes audio data from a CD-I disc image.',
        epilog=Sequencer.ARGS_EPILOG
    )

parser.add_argument('discfile', help='Disc image file to decode from')
parser.add_argument('--no-cd-headers', '-H', dest='headers', action='store_false', help='Image file does not have CD headers')

group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('cmdfile', nargs='?', help='Command file containing a sequence of reads to feed to the decoder.')
group.add_argument('--file', '-f', metavar='SPEC', action='append', dest='files', help='A specific filename, and optional channels / records, to decode.')

parser.add_argument('-y', type=int, help='Initial luminance, default is 0')
parser.add_argument('-u', type=int, help='Initial chrominance U, default is 0')
parser.add_argument('-v', type=int, help='Initial chrominance V, default is 0')

parser.add_argument('--width',  '-X', type=int, help='Image width to use, default is 384.')
parser.add_argument('--height', '-Y', type=int, help='Image height to use, default is 280.')

class OuterDecoder(object):
    def __init__(self, args):
        self.filename = None

        const_Y = 0 if args.y is None else args.y
        const_U = 0 if args.u is None else args.u
        const_V = 0 if args.v is None else args.v

        w = 384 if args.width  is None else args.width
        h = 280 if args.height is None else args.height

        self.iv_func = lambda y: (const_Y, const_U, const_V)
        self.size = (w, h)

    def set_output(self, filename):
        self.image_number = 0
        self.filename = filename

    def _video_blocks(self, blocks):
        for block in blocks:
            if block.subheader.video and block.subheader.coding.encoding == cdi.sector.VideoCoding.ENCODING_DYUV:
                yield block

    def decode(self, blocks):
        decoder = cdi.formats.dyuv.DYUVDecoder(self._video_blocks(blocks))
        decoder.initial_values(self.iv_func)
        decoder.size(*self.size)

        for image in decoder.decode_all_images():
            outfn = '{:s}.img{:04d}.png'.format(self.filename, self.image_number)
            print('Saving image {:s}'.format(outfn))
            image.convert(mode='RGB').save(outfn)
            self.image_number += 1

args = parser.parse_args()

print("Opening disc image file '{:s}'".format(args.discfile))
img = cdi.Image(args.discfile, headers=args.headers)

seq = Sequencer(img, OuterDecoder(args))
seq.from_args(args)
