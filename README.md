CSGO Demo/Replay event dump

TODO: List events of specific types, with customizable filters
Or just list everything but use a really greppable format

Or maybe dump stuff in JSON and let someone else parse it.

For the heatmap, radar images can be obtained from the CSGO
installation directory and converted to PNG using ImageMagick
(see Makefile for an example).

TODO: Time-based or match-based averaging, possibly rolling, so
you can scrub through a timeline and see how you've been going.

TODO: Restrict stats to a specific rectangle - probably has to
be baked in. Would exclude all data points outside it, allowing
the scaling to readjust.

TODO: Use different colours for different stats.

TODO: K/D filtered to whether we then won or lost the round


Licensed under the terms of the MIT License (MIT)

Copyright (c) 2021 Chris Angelico

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
