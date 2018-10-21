#!/usr/bin/env python3

import argparse
import sys
import os
import wave

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import cdi
import cdi.formats.audio
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

decoder = None
outfile = None
filename = None

initialized = False

class OuterDecoder(object):
    def __init__(self):
        self.outfile = None
        self.decoder = None

    def set_output(self, filename):
        self.decoder = cdi.formats.audio.AudioDecoder()

        if not self.outfile is None:
            self.outfile.close()
        
        self.outfile = None
        self.filename = '{:s}.wav'.format(filename)

    def decode(self, blocks):
        for block in blocks:
            if self.decoder is None:
                raise RuntimeError('Output file was not specified before decoding started')

            if not block.subheader.audio:
                continue

            samples = bytearray()
            for samp in self.decoder.decode_block(block):
                samples.append( samp & 0b0000000011111111      )
                samples.append((samp & 0b1111111100000000) >> 8)

            if self.outfile is None:
                print("Opening output file '{:s}'".format(self.filename))
                self.outfile = wave.open(self.filename, 'wb')
                self.outfile.setnchannels(2 if self.decoder.stereo else 1)
                self.outfile.setsampwidth(2)
                self.outfile.setframerate(self.decoder.sample_rate)

            self.outfile.writeframes(samples)

    def handle_command(self, command, args):
        raise RuntimeError("Unknown command '{:s}'".format(command))

args = parser.parse_args()

print("Opening disc image file '{:s}'".format(args.discfile))
img = cdi.Image(args.discfile, headers=args.headers)
seq = Sequencer(img, OuterDecoder())
seq.from_args(args)
