from cdi import *
import wave
import array
import argparse
import sys

# a lookup list for the index of each parameter byte in the sound group header
PARAM_IDX = range(4,12)

class ADPCMDec:
    "ADPCM decoder"

    def __init__(self):
        self.delayed1 = 0.     # two delay lines
        self.delayed2 = 0.
        self.G        = 0      # gain
        self.K0       = 0.     # first order filter coefficient
        self.K1       = 0.     # second order filter coefficient

    def set_params(self, G, F):
        # set range (exponential gain) value
        self.G = int(G)

        # set predictor filter
        if F == 0:
            self.K0 =  0.
            self.K1 =  0.
        elif F == 1:
            self.K0 =  0.9375
            self.K1 =  0.
        elif F == 2:
            self.K0 = 1.796875
            self.K1 = -0.8125
        elif F == 3:
            self.K0 =  1.53125
            self.K1 = -0.859375
        else:
            raise ValueError("Invalid filter setting %d" % F)

    def reset(self):
        self.delayed1 = 0.
        self.delayed2 = 0.

    def propagate(self, data):
        output = data * 2.**self.G  +  self.delayed1 * self.K0  +  self.delayed2 * self.K1
        output = max(-2**15, min(2**15-1, int(output)))
        self.delayed2 = self.delayed1
        self.delayed1 = output
        return output


def sign_extend(v):
    "Convert 4-bit two's complement to python int"
    if v & (1<<3):
        return (v & ~(1<<3)) - (1<<3)
    else:
        return v

def extract_params(p):
    "Extract ADPCM parameters (range, filter) from byte."
    return ord(p)&0b00001111, (ord(p)&0b11110000) >> 4

def extract_chans(d):
    "Extract channel data (left, right) from byte"
    return sign_extend(ord(d)&0b00001111), sign_extend((ord(d)&0b11110000) >> 4)

# parse command-line arguments
parser = argparse.ArgumentParser(description='Decode audio data from an extracted CD-I audio track')
parser.add_argument('input_file',   help='Track file to decode')
parser.add_argument('output_file',  help='Output file name')
parser.add_argument('--ignore-other', '-i', action='store_true', help='Ignore non-audio sectors in file')

args = parser.parse_args()

# initialize
infile  = open(args.input_file, 'rb')   # input file
indisc  = Disc(infile)                  # input Disc object (not a full disc image)
outsamples = array.array("h")

current_sector = 0
offset = 0
encoding = None
print "%s:" % args.input_file,

decoder = ADPCMDec()

while offset < indisc.image_file.size():
    sector = Sector(indisc, offset)

    sh = sector.subheader
    if not sh.audio:
        if args.ignore_other:
            offset += sector.FULL_SIZE
            current_sector += 1
            continue
        else:
            raise RuntimeError("Found non-audio sector in file")

    # determine encoding
    if encoding is None:
        encoding = sh.coding_raw
        assert not (sh.coding_raw & (1<<5)), "Reserved sample width specified in encoding"
        sample_width = 8 if (sh.coding_raw & (1<<4)) else 4

        assert not (sh.coding_raw & (1<<3)), "Reserved sample rate specified in encoding"
        sample_rate  = 18900 if (sh.coding_raw & (1<<2)) else 37800

        assert not (sh.coding_raw & (1<<1)), "Reserved channel number specified in encoding"
        stereo = True if (sh.coding_raw & (1<<0)) else False

        if stereo:
            decoder_l = ADPCMDec()
            decoder_r = ADPCMDec()
        else:
            decoder = ADPCMDec()

        print "%dHz, %dbit, %s "%(sample_rate, sample_width, "stereo" if stereo else "mono"),
    else:
        assert encoding == sh.coding_raw, "Entire file must have same encoding"

    if current_sector > 0:
        sys.stdout.write('\b' * 8)

    sys.stdout.write('%5d...' % current_sector)
    sys.stdout.flush()
    current_sector += 1

    # read sound groups in sector
    for group in range(18):
        sound_group   = sector[Subheader.SIZE+group*128:Subheader.SIZE+(group+1)*128]

        if sample_width == 8:
            for i in range(4):
                for j in range(1,4):
                    assert sound_group[i] == sound_group[i+4*j]

            # level A audio
            for unit in xrange(4):
                R, F = extract_params(sound_group[unit])
                decoder.set_params(8-R, F)
                for sample in xrange(28):
                    D = ord(sound_group[16+unit+4*sample])
                    outsamples.append(decoder.propagate(D))

        elif sample_width == 4:
            # level B or C audio
            for i in range(4):
                assert sound_group[i]   == sound_group[i+4]
                assert sound_group[i+8] == sound_group[i+12]

            if stereo:
                for unit in xrange(4):
                    R1, F1 = extract_params(sound_group[PARAM_IDX[unit*2]])
                    R2, F2 = extract_params(sound_group[PARAM_IDX[unit*2+1]])
                    decoder_l.set_params(12-R1, F1)
                    decoder_r.set_params(12-R2, F2)

                    for sample in xrange(28):
                        D1, D2 = extract_chans(sound_group[16+unit+4*sample])
                        outsamples.append(decoder_l.propagate(D1))
                        outsamples.append(decoder_r.propagate(D2))

            else:
                for unit in xrange(8):
                    R, F = extract_params(sound_group[PARAM_IDX[unit]])
                    decoder.set_params(12-R, F)

                    for sample in xrange(28):
                        D1, D2 = extract_chans(sound_group[16+(unit//2)+4*sample])
                        if unit%2 == 0:
                            outsamples.append(decoder.propagate(D1))
                        else:
                            outsamples.append(decoder.propagate(D2))

    offset += sector.FULL_SIZE

print " done."

if len(outsamples) == 0:
    sys.exit(0)

# write output file
outfile = wave.open(args.output_file, 'wb')
outfile.setnchannels(2 if stereo else 1)
outfile.setsampwidth(2)
outfile.setframerate(sample_rate)
samples = ""
for samp in outsamples:
    samples += chr(samp&0b0000000011111111) + chr((samp&0b1111111100000000) >> 8)
outfile.writeframes(samples)
