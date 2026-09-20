# SPDX-License-Identifier: LGPL-3.0-or-later

"""Round-trip tests for the 1-bit RLE encoder.

The decoder on the watch starts every image on the background colour and flips
on each run, so an image whose first pixel is foreground needs an empty run in
front of it. Get that wrong and the whole image draws inverted, which is easy
to miss on a dark theme.
"""

import os.path
import sys

import pytest
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rle_encode


def decode(image):
    """Decode exactly as Draw565.rleblit does."""
    (sx, sy, rle) = image
    pixels = []
    color = 0
    for rl in rle:
        pixels.extend([color] * rl)
        color ^= 1
    return [pixels[y * sx:(y + 1) * sx] for y in range(sy)]


def make(rows):
    """Build a 1-bit image from rows of 0s and 1s."""
    im = Image.new('1', (len(rows[0]), len(rows)), 0)
    px = im.load()
    for (y, row) in enumerate(rows):
        for (x, v) in enumerate(row):
            px[x, y] = v
    return im


PATTERNS = {
    'background first': [[0, 0, 1, 1], [0, 0, 1, 1]],
    'foreground first': [[1, 1, 0, 0], [1, 1, 0, 0]],
    'all background': [[0, 0], [0, 0]],
    'all foreground': [[1, 1], [1, 1]],
    'single foreground pixel': [[1, 0], [0, 0]],
    'alternating': [[1, 0, 1, 0], [0, 1, 0, 1]],
}


@pytest.mark.parametrize('name', sorted(PATTERNS))
def test_round_trip(name):
    rows = PATTERNS[name]
    decoded = decode(rle_encode.encode(make(rows)))
    assert decoded == rows, name


def test_mirrored_images_survive():
    """A mirror flips which colour comes first, which is how corners broke."""
    rows = [[0, 0, 1, 1], [0, 1, 1, 1]]
    im = make(rows)
    flipped = im.transpose(Image.FLIP_LEFT_RIGHT)
    expected = [list(reversed(r)) for r in rows]
    assert decode(rle_encode.encode(flipped)) == expected


def test_run_longer_than_255():
    """Long runs split into 255 plus an empty run of the other colour."""
    rows = [[0] * 300, [1] * 300]
    assert decode(rle_encode.encode(make(rows))) == rows
