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

parser.add_argument('-y', type=int, help='Initial luminance (try 0 first)')
parser.add_argument('-u', type=int, help='Initial chrominance U (try 0 first)')
parser.add_argument('-v', type=int, help='Initial chrominance V (try 0 first)')


class OuterDecoder(object):
    def __init__(self, args):
        self.filename = None

        const_Y = 0 if args.y is None else args.y
        const_U = 0 if args.u is None else args.u
        const_V = 0 if args.v is None else args.v

        self.iv_func = lambda y: (const_Y, const_U, const_V)

    def set_output(self, filename):
        self.filename = filename

    def decode(self, blocks):
        video_blocks = (block for block in blocks if block.subheader.video and block.subheader.coding.encoding == cdi.sector.VideoCoding.ENCODING_DYUV)

        decoder = cdi.formats.dyuv.DYUVDecoder(video_blocks)
        decoder.initial_values(self.iv_func)

        for n, image in enumerate(decoder.decode_all_images()):
            image.convert(mode='RGB').save('{:s}.img{:04d}.png'.format(self.filename, n))

args = parser.parse_args()

print("Opening disc image file '{:s}'".format(args.discfile))
img = cdi.Image(args.discfile, headers=args.headers)

seq = Sequencer(img, OuterDecoder(args))
seq.from_args(args)
