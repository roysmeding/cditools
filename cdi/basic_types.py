# shorthand parsing methods. They take a sequence of characters (bytes) as input.
def number(seq):
    out = 0
    for c in seq:
        out = 256*out + c
    return out

def rawstring(seq, encoding='iso-8859-1'):
    return seq.decode(encoding)

def string(seq, encoding='iso-8859-1'):
    return rawstring(seq, encoding).rstrip()
