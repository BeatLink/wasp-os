# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (C) 2020 Daniel Thompson

def __getattr__(name):
    """Import a font the first time it is used."""
    if name not in ('sans18', 'sans24', 'sans28', 'sans36'):
        raise AttributeError(name)
    return __import__('fonts.' + name, None, None, (name,))

def height(font):
    return font.height()

def width(font, s):
    w = 0
    for ch in s:
        (_, _, wc) = font.get_ch(ch)
        w += wc + 1

    return w


