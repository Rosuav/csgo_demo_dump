CSGO Demo/Replay event dump

TODO: List events of specific types, with customizable filters
Or just list everything but use a really greppable format

Or maybe dump stuff in JSON and let someone else parse it.

For the heatmap, radar images can be obtained from the CSGO
installation directory and converted to PNG using ImageMagick.

TODO: Save the data in a way that makes it easy to add another
demo file without regenerating everything.

TODO: Time-based or match-based averaging, possibly rolling, so
you can scrub through a timeline and see how you've been going.

TODO: Restrict stats to a specific rectangle - probably has to
be baked in. Would exclude all data points outside it, allowing
the scaling to readjust.
