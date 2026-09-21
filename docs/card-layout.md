# Card layout

Cards are the rounded rectangles that wasp-os pages are built from: launcher
tiles, list rows, the keypads in the alarm app. They come from one set of
numbers in [`wasp/cards.py`](../wasp/cards.py), so that pages drawn by
different apps line up with one another.

## The numbers

| Name | Value | Meaning |
| --- | --- | --- |
| `MARGIN` | 4 | Space left clear around the edge of the screen |
| `GAP` | 3 | Smallest space allowed between two cards |
| `SPAN` | 232 | Width and height left for cards, `240 - 2 * MARGIN` |
| `COLOR` | `0x3186` | Card grey, chosen to let white content carry the page |
| `SCROLLBAR` | 2 | Width of the scroll bar |
| `SCROLLBAR_X` | 238 | Where the scroll bar starts |

The corner radius is deliberately absent. It belongs to
[`res/ui/corner.svg`](../res/ui/corner.svg), which is baked into four bitmaps
at build time, and `Draw565.rounded_rect` takes it from there. Changing the
radius means redrawing the corner, not editing a constant.

## Sizing a row or column

`size(count)` gives the width or height of each card when `count` of them
share the span. Cards are made as large as the span allows while keeping at
least `GAP` between them:

| Cards | Size |
| --- | --- |
| 1 | 232 |
| 2 | 114 |
| 3 | 75 |
| 4 | 55 |

`edges(sizes)` gives the left or top edge of each card. Whatever space the
cards do not use is shared out between them, so a row always reaches both
margins however its sizes divide up. It takes a size per card rather than a
count, which lets a page mix them — the alarm summary is one tall card above
two short ones.

```python
_TILE = cards.size(3)                    # 75
_EDGES = cards.edges((_TILE,) * 3)       # (4, 83, 161)
```

Call `edges` once when the module loads, not on every redraw. Every layout in
the tree is derived this way rather than written out, so a page is a few
numbers instead of an asset.

## The scroll bar

Cards reach x=236, leaving two clear pixels before the bar at x=238. The bar
is drawn by `scrollbar()`, one segment per page down the right hand edge, in
two greys against the black background: the current page in the
`scroll-indicator` theme colour and the rest in the card grey. It draws
nothing when there is only one page.

```python
cards.scrollbar(draw, self._page, self._num_pages,
                wasp.system.theme('scroll-indicator'))
```

It marks position on any vertical axis, not only a scrolling list. The alarm
app uses it twice: for the pages of its list, and for the three pages of its
editor.

## Working on the vertical axis

Pages move up and down rather than left and right wherever there is a choice.
The launchers page vertically, and the alarm editor steps between its three
pages on the same axis, leaving left and right free.

This is partly consistency and partly groundwork. The ST7789V will scroll its
own memory vertically for the cost of a register write, which is the only way
an animated scroll fits the SPI budget; see
[`scroll-animation-design.md`](scroll-animation-design.md). A UI that already
moves vertically can adopt that without changing how it is driven.
