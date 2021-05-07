import json
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
	# Colours for simple heatmaps
	RGB_LOW = (0, 64, 0, 192)
	RGB_HIGH = (240, 255, 240, 255)
	# Colours for ratio heatmaps
	RGB_LOW_POS = (0, 0, 64, 192)
	RGB_HIGH_POS = (240, 240, 255, 255)
	RGB_LOW_NEG = (64, 0, 0, 192)
	RGB_HIGH_NEG = (255, 240, 240, 255)
	fn: str
	image: list
	peak: float = 0.0
	negpeak: float = 0.0 # Will stay permanently at 0.0 for non-ratio heatmaps
	first: int = 1<<64 # Timestamps
	last: int = 0
	def floor(self, peak): # Calculate the floor given a particular peak value. Reduces graph blotchiness.
		return max(0.875, peak / 16)
	@classmethod
	def get(cls, func, name, team):
		key = (func, name, team)
		if key not in heatmaps: heatmaps[key] = cls(
			fn=f"{func.__name__}_{name}_{team}",
			image=[[0.0] * IMAGE_WIDTH for _ in range(IMAGE_HEIGHT)],
		)
		return heatmaps[key]
	def save(self):
		max = (self.peak, self.negpeak)
		min = [self.floor(p) for p in max] # min = self.floor(max[*])
		span = [p - f for p, f in zip(max, min)] # span = max[*] - min[*]
		if self.negpeak:
			rgb_low = [self.RGB_LOW_POS, self.RGB_LOW_NEG]
			rgb_high = [self.RGB_HIGH_POS, self.RGB_HIGH_NEG]
		else:
			rgb_low, rgb_high = [self.RGB_LOW], [self.RGB_HIGH]
		colordata = []
		for row in self.image:
			out = []
			for value in row:
				q = value < 0
				if q: value = -value
				if value > max[q]: value = max[q]
				# Interpolate a colour value between min and max
				# If below min, fully transparent, else interp
				# each channel independently.
				if value <= min[q]:
					out.extend((0, 0, 0, 0))
					continue
				value = (value - min[q]) / span[q]
				for lo, hi in zip(rgb_low[q], rgb_high[q]):
					out.append(int(lo + (hi - lo) * value))
			colordata.append(out)
		return png.from_array(colordata, "RGBA").save(self.fn + ".png")

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

def add_dot_to_image(heatmap, timestamp, x, y, value):
	heatmap.first = min(heatmap.first, timestamp)
	heatmap.last = max(heatmap.last, timestamp)
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
@finder("kill")
def kills_self(params):
	"Kills (self)"
	return params[0], params[3], 1
@finder("kill")
def kills_victim(params):
	"Kills (victim)"
	return params[0], params[4], 1
@finder("death")
def death_self(params):
	"Deaths (self)"
	return params[0], params[4], 1
@finder("death")
def death_killer(params):
	"Deaths (killer)"
	if params[3]: return params[0], params[3], 1 # If I die to a non-person, ignore it
# Entry kills/deaths are worth tracking too
@finder("kill")
def entry_kills_self(params):
	"Entry kills (self)"
	if "E" not in params[1]: return None
	return params[0], params[3], 1
@finder("kill")
def entry_kills_victim(params):
	"Entry kills (victim)"
	if "E" not in params[1]: return None
	return params[0], params[4], 1
@finder("death")
def entry_death_self(params):
	"Entry deaths (self)"
	if "E" not in params[1]: return None
	return params[0], params[4], 1
@finder("death")
def entry_death_killer(params):
	"Entry deaths (killer)"
	if "E" not in params[1]: return None
	if params[3]: return params[0], params[3], 1
# Ratios are done a bit weirdly. The finder is a function from above,
# and the decorated function has to return another such function.
@finder(kills_self)
def kd_self():
	"K/D (self)"
	return death_self
@finder(kills_victim)
def kd_other():
	"K/D (other)"
	return death_killer

with open("demodata.json") as f:
	data = json.load(f)

limit = -1
for filename in sorted(data, reverse=True):
	if filename == "codehash": continue
	if not limit: break
	limit -= 1
	print(filename)
	teams = { }
	for line in data[filename]:
		key, *params = line.strip().split(":")
		if key == "date":
			timestamp = int(params[0])
			continue
		if key == "player":
			teams[params[2]] = params[4]
			continue
		tick, round, tm, *params = params # Most lines have timestamping information
		if key == "round_start" and round == "R16":
			# We don't get the cs_intermission event, so this is our cue that
			# everyone's teams have switched.
			for person, t in teams.items():
				teams[person] = "T" if t == "C" else "C" # assume no spectators
		if round == "R0": continue # Warmup is uninteresting
		for func in finders[key]:
			try:
				who, where, value = func(params) or ('', '', 0)
				if not value: continue
				x, y, *_ = where.split(",") # Will have a z coordinate; may also have pitch and yaw.
				for teamtag in ("A", teams[who]):
					add_dot_to_image(Heatmap.get(func, who.split()[0], teamtag), timestamp, float(x), float(y), value)
			except Exception:
				print(key, tick, round, tm, params)
				raise

# Go through and find all the things to multiply. Everything other than the
# function has to match, and will be retained in the result.
for (func1, *info), img1 in list(heatmaps.items()): # Ensure that we don't try to do ratios of ratios
	for func2 in finders[func1]:
		img2 = heatmaps.get((func2(), *info))
		if not img2: continue
		target = Heatmap.get(func2, *info)
		target.first = min(img1.first, img2.first)
		target.last = max(img1.last, img2.last)
		peak1, peak2 = img1.peak, img2.peak
		floor1, floor2 = img1.floor(peak1), img2.floor(peak2)
		for row1, row2, trow in zip(img1.image, img2.image, target.image):
			for i, (value1, value2) in enumerate(zip(row1, row2)):
				# If both values are below their corresponding floors, leave it zero.
				# If one value is, treat the other as if it's precisely its floor (to
				# avoid stupidly big values 
				# Whichever value is higher, divide it by the other, and put that in.
				if value1 < floor1 and value2 < floor2: continue # No useful data here.
				value1 = max(value1, floor1); value2 = max(value2, floor2)
				if value1 < value2:
					v = value2 / value1
					target.negpeak = max(target.negpeak, v)
					trow[i] = -v
				else:
					v = value1 / value2
					target.peak = max(target.peak, v)
					trow[i] = v

# Heatmap.get(lambda: 0, "", "").fn = "output" # Uncomment to create output.png, a blank image. Optionally with colour gauge (below).
timestamps = { }
for img in heatmaps.values():
	# Add a colour gauge at the top for debugging
	# for r in range(10): img[r][:] = [img_peaks[fn] * (i + 1) / IMAGE_WIDTH for i in range(IMAGE_WIDTH)]
	img.save()
	timestamps[img.fn] = [img.first, img.last]
	print("%s.png [%.3f, %.3f]" % (img.fn, img.floor(img.peak), img.peak))
with open("template.html") as t, open("heatmap.html", "w") as f:
	f.write(t.read()
		.replace("$$radiobuttons$$", "".join("<ul>" + "".join(
			f"<li><label><input type=radio name={opt} value=%s> %s</label></li>" % kv for kv in choices.items()
		) + "</ul>" for opt, choices in options.items()))
		.replace("$$radio_names$$", ", ".join('"%s"' % opt for opt in options))
		.replace("$$timestamps$$", json.dumps(timestamps))
	)
