#!/usr/bin/env python3

# SPDX-License-Identifier: LGPL-3.0-or-later

"""Generate the monochrome app icons used by the launcher.

Each icon is a Font Awesome 6 Solid glyph rendered white on black, saved as a
PNG next to the app that uses it and then encoded as a 1-bit RLE image. A 1-bit
image is drawn with the foreground and background colours chosen at draw time,
so the launcher can paint the icon straight onto its tile.

Run this from the top of the tree whenever an icon or a glyph choice changes.
"""

import json
import os.path
import re
import subprocess
import sys

from PIL import Image, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rle_encode

FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    'fontawesome', 'FontAwesome6_Solid.ttf')
GLYPHMAP = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'fontawesome', 'glyphmap.json')

# Size of the square the glyph is fitted into.
SIZE = 32

# The launcher tiles, drawn behind the icons.
BACKGROUNDS = (
    ('wasp/apps/system/grid_launcher.py', 'background',
     'res/ui/backgrounds/3x3.png', 'res/ui/backgrounds/3x3.svg'),
    ('wasp/apps/system/list_launcher.py', 'background',
     'res/ui/backgrounds/4x1.png', 'res/ui/backgrounds/4x1.svg'),
)

# Glyph for each app, as (source file, variable, PNG, glyph name).
ICONS = (
    ('apps/alarm/app.py', 'icon', 'apps/alarm/icon.png', 'bell'),
    ('apps/beacon/app.py', 'ICON', 'apps/beacon/icon.png', 'tower-broadcast'),
    ('apps/calculator/app.py', 'calc', 'apps/calculator/icon.png', 'calculator'),
    ('apps/demo/app.py', 'demo_icon', 'apps/demo/icon.png', 'wand-magic-sparkles'),
    ('apps/disa_b_l_e/app.py', 'ICON', 'apps/disa_b_l_e/icon.png', 'ban'),
    ('apps/four_in_a_row/app.py', 'icon', 'apps/four_in_a_row/icon.png', 'circle-dot'),
    ('apps/gallery/app.py', 'ICON', 'apps/gallery/icon.png', 'image'),
    ('apps/game_of_life/app.py', 'icon', 'apps/game_of_life/icon.png', 'table-cells'),
    ('apps/haiku/app.py', 'icon', 'apps/haiku/icon.png', 'feather-pointed'),
    ('apps/heart/app.py', 'icon', 'apps/heart/icon.png', 'heart-pulse'),
    ('apps/hello/app.py', 'icon', 'apps/hello/icon.png', 'hand'),
    ('apps/level/app.py', 'ICON', 'apps/level/icon.png', 'ruler-horizontal'),
    ('apps/morse/app.py', 'ICON', 'apps/morse/icon.png', 'tower-cell'),
    ('apps/music_player/app.py', 'icon', 'apps/music_player/icon.png', 'music'),
    ('apps/phone_finder/app.py', 'icon', 'apps/phone_finder/icon.png', 'mobile-screen-button'),
    ('apps/pomodoro/app.py', 'icon', 'apps/pomodoro/icon.png', 'hourglass-half'),
    ('apps/puzzle15/app.py', 'icon', 'apps/puzzle15/icon.png', 'puzzle-piece'),
    ('apps/read_me/app.py', 'icon', 'apps/read_me/icon.png', 'book-open'),
    ('apps/snake/app.py', 'snake_icon', 'apps/snake/icon.png', 'worm'),
    ('apps/sports/app.py', 'icon', 'apps/sports/icon.png', 'person-running'),
    ('apps/stopwatch/app.py', 'icon', 'apps/stopwatch/icon.png', 'stopwatch'),
    ('apps/test/app.py', 'icon', 'apps/test/icon.png', 'flask'),
    ('apps/timer/app.py', 'icon', 'apps/timer/icon.png', 'hourglass'),
    ('apps/weather/app.py', 'icon', 'apps/weather/icon.png', 'cloud-sun'),

    ('wasp/icons.py', 'app', 'wasp/resources/app_icon.png', 'shapes'),
    ('wasp/icons.py', 'clock', 'wasp/resources/clock_icon.png', 'clock'),
    ('wasp/icons.py', 'settings', 'wasp/resources/settings_icon.png', 'gear'),
    ('wasp/icons.py', 'software', 'wasp/resources/software_icon.png', 'download'),
    ('wasp/icons.py', 'torch', 'wasp/resources/torch_icon.png', 'lightbulb'),
    ('wasp/icons.py', 'steps', 'wasp/resources/steps_icon.png', 'shoe-prints'),
)


def render(codepoint):
    """Render one glyph, white on black, fitted into a SIZE square."""
    # Render large, then scale the inked area down, so the glyph fills the box.
    font = ImageFont.truetype(FONT, 4 * SIZE)
    mask = font.getmask(chr(codepoint), mode='L')
    glyph = Image.frombytes('L', mask.size, bytes(mask))
    glyph = glyph.crop(glyph.getbbox())

    scale = min(SIZE / glyph.width, SIZE / glyph.height)
    glyph = glyph.resize((max(1, round(glyph.width * scale)),
                          max(1, round(glyph.height * scale))),
                         Image.LANCZOS)

    im = Image.new('L', (SIZE, SIZE), 0)
    im.paste(glyph, ((SIZE - glyph.width) // 2, (SIZE - glyph.height) // 2))
    return im.point(lambda p: 255 if p >= 128 else 0).convert('1')


def replace(source, name, image, png):
    """Replace the RLE literal for name in source with image."""
    with open(source) as f:
        lines = f.readlines()

    opening = re.compile(r'^([ \t]*)' + re.escape(name) + r' = \($')
    start = None
    for (i, line) in enumerate(lines):
        match = opening.match(line.rstrip('\n'))
        if match:
            start = i
            indent = match.group(1)
            break
    if start is None:
        raise SystemExit('{}: no literal named {}'.format(source, name))

    # The literal runs to the last of its continuation lines, which are always
    # indented further than the assignment itself.
    end = start + 1
    while end < len(lines) and lines[end].startswith(indent + ' '):
        end += 1
    if end < len(lines) and lines[end].strip() == ')':
        end += 1

    # Absorb the comment naming the source image, so it stays accurate.
    if start and lines[start-1].strip().startswith('#'):
        start -= 1

    body = rle_encode.render_py_str(image, png, 0, 1, name)
    body = [indent + l if l.strip() else l for l in body.splitlines(True)]

    with open(source, 'w') as f:
        f.writelines(lines[:start] + body + lines[end:])


def bake(svg, png):
    """Render an SVG to a monochrome PNG the size of the screen."""
    subprocess.run(('inkscape', '--export-type=png', '--export-width=240',
                    '--export-height=240', '--export-background=black',
                    '--export-filename=' + png, svg), check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    im = Image.open(png).convert('L')
    im = im.point(lambda p: 255 if p >= 128 else 0).convert('1')
    im.save(png)
    return im


def main():
    glyphs = json.load(open(GLYPHMAP))

    for (source, name, png, svg) in BACKGROUNDS:
        replace(source, name, rle_encode.encode(bake(svg, png)), svg)
        print('{:<40} {:<24} {}'.format(source, name, svg))

    for (source, name, png, glyph) in ICONS:
        if glyph not in glyphs:
            raise SystemExit('no such glyph: ' + glyph)
        im = render(glyphs[glyph])
        im.save(png)
        replace(source, name, rle_encode.encode(Image.open(png)), png)
        print('{:<40} {:<24} {}'.format(source, name, glyph))


if __name__ == '__main__':
    main()
