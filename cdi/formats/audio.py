# CD-I discs can have audio sectors encoded in adaptive delta pulse code
# modulation (ADPCM).

import array

from ..sector import AudioCoding

class ADPCMDec:
    """ADPCM decoder

    Contains the state necessary to decode one ADCPM audio stream.
    """

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
    "Convert a single packed parameter byte to separate (range, filter) values"
    return p & 0b00001111, (p & 0b11110000) >> 4

def extract_chans(d):
    "Convert a single packed data byte to separate (left, right) values"
    return sign_extend(d & 0b00001111), sign_extend((d & 0b11110000) >> 4)


class AudioDecoder(object):
    """Decodes CD-I audio data from a disc file"""

    GROUP_SIZE = 128
    N_GROUPS = 18
    SAMPLES_PER_UNIT = 28

    # a lookup list for the index of each parameter byte in the sound group header
    PARAM_IDX = range(4,12)

    def __init__(self):
        self.initialized = False

    def _initialize_encoders(self, sh):
        if   sh.coding.sample_depth == AudioCoding.SAMPLE_DEPTH_8BIT:
            self.sample_depth = 8

        elif sh.coding.sample_depth == AudioCoding.SAMPLE_DEPTH_4BIT:
            self.sample_depth = 4

        else:
            raise ValueError("Reserved sample depth specified in encoding")


        if   sh.coding.sample_rate == AudioCoding.SAMPLE_RATE_18900:
            self.sample_rate = 18900

        elif sh.coding.sample_rate == AudioCoding.SAMPLE_RATE_37800:
            self.sample_rate = 37800

        else:
            raise ValueError("Reserved sample rate specified in encoding")


        if   sh.coding.stereo:
            self.stereo = True
            
            self.decoder_l = ADPCMDec()
            self.decoder_r = ADPCMDec()

        elif sh.coding.mono:
            self.stereo = False
            
            self.decoder = ADPCMDec()

        else:
            raise ValueError("Reserved channel number specified in encoding")

        self.initialized = True

    def decode_block(self, block):
        """Decodes a single sector of audio."""

        if not self.initialized:
            self._initialize_encoders(block.subheader)

        outsamples = array.array("h")

        # read sound groups in sector
        for group in range(AudioDecoder.N_GROUPS):
            offset = group * AudioDecoder.GROUP_SIZE
            sound_group   = block.get_data(offset, offset+AudioDecoder.GROUP_SIZE)

            if self.sample_depth == 8:
                # level A audio
                for i in range(4):
                    for j in range(1,4):
                        assert sound_group[i] == sound_group[i+4*j]

                for unit in range(4):
                    R, F = extract_params(sound_group[unit])
                    decoder.set_params(8-R, F)

                    for sample in range(AudioDecoder.SAMPLES_PER_UNIT):
                        D = ord(sound_group[16+unit+4*sample])
                        outsamples.append(decoder.propagate(D))

            elif self.sample_depth == 4:
                # level B or C audio
                for i in range(4):
                    assert sound_group[i]   == sound_group[i+4]
                    assert sound_group[i+8] == sound_group[i+12]

                if self.stereo:
                    for unit in range(4):
                        R1, F1 = extract_params(sound_group[self.PARAM_IDX[unit*2]])
                        R2, F2 = extract_params(sound_group[self.PARAM_IDX[unit*2+1]])
                        self.decoder_l.set_params(12-R1, F1)
                        self.decoder_r.set_params(12-R2, F2)

                        for sample in range(AudioDecoder.SAMPLES_PER_UNIT):
                            D1, D2 = extract_chans(sound_group[16+unit+4*sample])
                            outsamples.append(self.decoder_l.propagate(D1))
                            outsamples.append(self.decoder_r.propagate(D2))

                else:
                    for unit in range(8):
                        R, F = extract_params(sound_group[self.PARAM_IDX[unit]])
                        self.decoder.set_params(12-R, F)

                        for sample in range(AudioDecoder.SAMPLES_PER_UNIT):
                            D1, D2 = extract_chans(sound_group[16+(unit//2)+4*sample])
                            if unit%2 == 0:
                                outsamples.append(self.decoder.propagate(D1))
                            else:
                                outsamples.append(self.decoder.propagate(D2))

        return outsamples
