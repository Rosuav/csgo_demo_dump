from collections import defaultdict
from dataclasses import dataclass, field
import png # pip install pypng

# (0,0) on the image should correspond to (MAP_XMIN, MAP_YMIN)
# If the coordinates need to be inverted, set (eg) XMIN to a high
# number and XMAX to a low number. Fine-tune to align the heatmap.
IMAGE_WIDTH = IMAGE_HEIGHT = 1024
MAP_XMIN = -2400; MAP_YMIN = 3150; MAP_XMAX = 1950; MAP_YMAX = -1200
MAP_WIDTH = MAP_XMAX - MAP_XMIN
MAP_HEIGHT = MAP_YMAX - MAP_YMIN
SPREAD_RADIUS = 16 # pixels (uses distance-squared dropoff)
# SPREAD_RANGE defines a square on which the spread will be calculated.
# For each pixel in the square, its real distance is calculated (finer
# resolution than the pixels), and the spread amount is calculated using
# linear dropoff that falls to zero at DECAY_RADIUS (which is dist^2).
SPREAD_RANGE = range(-SPREAD_RADIUS, SPREAD_RADIUS + 1)
DECAY_RADIUS = abs(MAP_WIDTH * MAP_HEIGHT / IMAGE_WIDTH / IMAGE_HEIGHT * SPREAD_RADIUS ** 2)

@dataclass
class Heatmap:
	fn: str
	image: list
	peak: float = 0.0
	@classmethod
	def get(cls, func, name, team):
		key = (func, name, team)
		if key not in heatmaps: heatmaps[key] = cls(
			fn=f"{func.__name__}_{name}_{team}",
			image=[[0.0] * IMAGE_WIDTH for _ in range(IMAGE_HEIGHT)],
		)
		return heatmaps[key]
heatmaps = { }
options = {
	"heatmap": { }, # Filled in below
	"name": {"Rosuav": "Rosuav", "Stephen": "Stephen"},
	"team": {"A": "All", "C": "CT", "T": "T"},
}

def img_to_map(x, y):
	return (
		MAP_WIDTH  * x / IMAGE_WIDTH  + MAP_XMIN,
		MAP_HEIGHT * y / IMAGE_HEIGHT + MAP_YMIN,
	)

def map_to_img(x, y):
	return (
		int((x - MAP_XMIN) * IMAGE_WIDTH  / MAP_WIDTH),
		int((y - MAP_YMIN) * IMAGE_HEIGHT / MAP_HEIGHT),
	)

def generate_image(img, min, max, rgb_low, rgb_high):
	span = max - min
	colordata = []
	for row in img:
		out = []
		for value in row:
			if value > max: value = max
			# Interpolate a colour value between min and max
			# If below min, fully transparent, else interp
			# each channel independently.
			if value <= min:
				out.extend((0, 0, 0, 0))
				continue
			value = (value - min) / span
			for lo, hi in zip(rgb_low, rgb_high):
				out.append(int(lo + (hi - lo) * value))
		colordata.append(out)
	return png.from_array(colordata, "RGBA")

def add_dot_to_image(heatmap, x, y, value):
	basex, basey = map_to_img(x, y)
	for dx in SPREAD_RANGE:
		for dy in SPREAD_RANGE:
			if basey + dy < 0 or basex + dx < 0: continue # No wrapping
			try: v = heatmap.image[basey + dy][basex + dx]
			except IndexError: continue # Past edge? No dot needed
			if dx or dy:
				altx, alty = img_to_map(basex + dx, basey + dy)
				dist = (altx - x) ** 2 + (alty - y) ** 2
				if dist >= DECAY_RADIUS: continue # It's in the corner of the square, too far to be relevant.
				v += value * (DECAY_RADIUS - dist) / DECAY_RADIUS
			else: v += value
			heatmap.image[basey + dy][basex + dx] = v
			heatmap.peak = max(heatmap.peak, v)

finders = defaultdict(list)
radiobuttons = []
def finder(key):
	def deco(func):
		finders[key].append(func)
		options["heatmap"][func.__name__] = func.__doc__
		return func
	return deco

@finder("smokegrenade_detonate")
def smoke(params):
	"Smoke throws"
	return params[0], params[1], 1
@finder("flash_hit") # Scored by opponents blinded
def flash_pop(params):
	"FB detonations"
	if params[1] in ("Self", "Team"): return None
	return params[0], params[2], float(params[4])
@finder("flash_hit") # Ditto.
def flash_hit(params):
	"FB victims"
	if params[1] in ("Self", "Team"): return None
	return params[0], params[3], float(params[4])

limit = -1
with open("all_data.txt") as f:
	teams = { }
	for line in f:
		if line.startswith("match730_"):
			# New demo file, identified by file name
			if not limit: break
			limit -= 1
			print(line.strip())
			teams = { }
			continue
		key, tick, round, tm, *params = line.strip().split(":")
		if key == "player":
			# This one is formatted differently - it doesn't have timing info.
			# The "tm" field actually gets the player name.
			teams[tm] = params[1]
			continue
		if key == "round_start" and round == "R16":
			# We don't get the cs_intermission event, so this is our cue that
			# everyone's teams have switched.
			for person, t in teams.items():
				teams[person] = "T" if t == "C" else "C" # assume no spectators
		if round == "R0": continue # Warmup is uninteresting
		for func in finders[key]:
			who, where, value = func(params) or ('', '', 0)
			if not value: continue
			x, y, *_ = where.split(",") # Will have a z coordinate; may also have pitch and yaw.
			for teamtag in ("A", teams[who]):
				add_dot_to_image(Heatmap.get(func, who.split()[0], teamtag), float(x), float(y), value)

# Heatmap.get(lambda: 0, "", "").fn = "output" # Uncomment to create output.png, a blank image. Optionally with colour gauge (below).
for img in heatmaps.values():
	# Add a colour gauge at the top for debugging
	# for r in range(10): img[r][:] = [img_peaks[fn] * (i + 1) / IMAGE_WIDTH for i in range(IMAGE_WIDTH)]
	generate_image(img.image, 0.875, img.peak, (0, 64, 0, 192), (240, 255, 240, 255)).save(img.fn + ".png")
	print(img.fn + ".png", img.peak)
with open("template.html") as t, open("heatmap.html", "w") as f:
	radiobuttons = "".join("<ul>" + "".join(
			f"<li><label><input type=radio name={opt} value=%s> %s</label></li>" % kv for kv in choices.items()
		) + "</ul>" for opt, choices in options.items())
	radio_names = ", ".join('"%s"' % opt for opt in options)
	f.write(t.read().replace("$$radiobuttons$$", radiobuttons).replace("$$radio_names$$", radio_names))
