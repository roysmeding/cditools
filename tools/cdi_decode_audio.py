import argparse
import sys
import os
import wave

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import cdi
import cdi.formats.audio

# parse command-line arguments
parser = argparse.ArgumentParser(description='Decodes audio from a CD-I disc image.')
parser.add_argument('image_file', help='Image file to decode from')
parser.add_argument('output_file', help='WAVE file to decode to')

parser.add_argument('--file',    '-f', default=None, help='Full path name of file to extract')
parser.add_argument('--record',  '-r', default=None, help='Record number to extract')
parser.add_argument('--channel', '-c', default=None, help='Channel number to extract')

parser.add_argument('--headers', '-H', action='store_true', help='Image file has CD headers')

def parse_range(v, default_start, default_end):
    if v is None:
        return range(default_start, default_end)

    else:
        parts = v.split('-')
        if   len(parts) == 1:
            if parts[0] == '':
                return range(default_start, default_end)
            else:
                idx = int(parts[0])
                return range(idx, idx+1)

        elif len(parts) == 2:
            start = int(parts[0]) if len(parts[0]) > 0 else default_start
            end   = int(parts[1]) if len(parts[1]) > 0 else default_end
            return range(start, end)

        else:
            raise ValueError

args = parser.parse_args()

img = cdi.Image(args.image_file, headers=args.headers)

if args.file is None:
    parser.print_help()
    sys.exit(1)

f = img.get_file(args.file)

try:
    records = parse_range(args.record, 0, len(f.records))
    channel = int(args.channel) if not args.channel is None else None

except ValueError:
    parser.print_help()
    sys.exit(1)

outfile = None

for record in records:
    audio_stream = cdi.formats.audio.AudioStream(f, record, channel)

    if outfile is None and not audio_stream.eof:
        outfile = wave.open(args.output_file, 'wb')
        outfile.setnchannels(2 if audio_stream.stereo else 1)
        outfile.setsampwidth(2)
        outfile.setframerate(audio_stream.sample_rate)

    while not audio_stream.eof:
        samples = bytearray()
        for samp in audio_stream.decode_block():
            samples.append(samp&0b0000000011111111)
            samples.append((samp&0b1111111100000000) >> 8)

        outfile.writeframes(samples)
