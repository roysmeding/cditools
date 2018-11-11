# default palettes for extracting CLUT / RL images
PALETTE8 = [
    (  0,  0,  0),
    (255,  0,  0),
    (  0,255,  0),
    (255,255,  0),
    (  0,  0,255),
    (255,  0,255),
    (  0,255,255),
    (255,255,255),
]

PALETTE16 = [
    (  0,  0,  0),
    (128,  0,  0),
    (  0,128,  0),
    (128,128,  0),
    (  0,  0,128),
    (128,  0,128),
    (  0,128,128),
    (128,128,128),
    (192,192,192),
    (255,  0,  0),
    (  0,255,  0),
    (255,255,  0),
    (  0,  0,255),
    (255,  0,255),
    (  0,255,255),
    (255,255,255),
]

def _gen_484():
    for r in range(0, 256, 64):
        for g in range(0, 256, 32):
            for b in range(0, 256, 64):
                yield (r, g, b)
PALETTE128 = list(_gen_484())

def _gen_884():
    for r in range(0, 256, 32):
        for g in range(0, 256, 32):
            for b in range(0, 256, 64):
                yield (r, g, b)
PALETTE256 = list(_gen_884())
