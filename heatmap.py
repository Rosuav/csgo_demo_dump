from collections import defaultdict
import png # pip install pypng

# (0,0) on the image should correspond to (MAP_XMIN, MAP_YMIN)
# If the coordinates need to be inverted, set (eg) XMIN to a high
# number and XMAX to a low number. Fine-tune to align the heatmap.
IMAGE_WIDTH = IMAGE_HEIGHT = 1024
MAP_XMIN = -2400; MAP_YMIN = 3150; MAP_XMAX = 1950; MAP_YMAX = -1200
MAP_WIDTH = MAP_XMAX - MAP_XMIN
MAP_HEIGHT = MAP_YMAX - MAP_YMIN
SPREAD_RADIUS = 16 # pixels (uses quadratic dropoff)
# SPREAD_RANGE defines a square on which the spread will be calculated.
# For each pixel in the square, its real distance is calculated (finer
# resolution than the pixels), and the spread amount is calculated using
# quadratic dropoff that falls to zero at DECAY_RADIUS (which is dist^2).
SPREAD_RANGE = range(-SPREAD_RADIUS, SPREAD_RADIUS + 1)
DECAY_RADIUS = abs(MAP_WIDTH * MAP_HEIGHT / IMAGE_WIDTH / IMAGE_HEIGHT * SPREAD_RADIUS ** 2)

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

def build_map(data):
	img = [[0.0] * IMAGE_WIDTH for _ in range(IMAGE_HEIGHT)]
	peak = 0
	for x, y, value in data:
		basex, basey = map_to_img(x, y)
		for dx in SPREAD_RANGE:
			for dy in SPREAD_RANGE:
				v = img[basey + dy][basex + dx]
				if dx or dy:
					altx, alty = img_to_map(basex + dx, basey + dy)
					dist = (altx - x) ** 2 + (alty - y) ** 2
					if dist >= DECAY_RADIUS: continue # It's in the corner of the square, too far to be relevant.
					v += value * ((DECAY_RADIUS - dist) / DECAY_RADIUS) ** 0.5
					# print("%.3f %3d %d %d %.3f" % (dist, dx**2+ dy**2, dx, dy, ((DECAY_RADIUS - dist) / DECAY_RADIUS) ** 0.5))
				else: v += value
				img[basey + dy][basex + dx] = v
				peak = max(peak, v)
	return img, peak

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
			if value < min:
				out.extend((0, 0, 0, 0))
				continue
			value = (value - min) / span
			for lo, hi in zip(rgb_low, rgb_high):
				out.append(int(lo + (hi - lo) * value))
		colordata.append(out)
	return png.from_array(colordata, "RGBA")

def add_dot_to_image(img, x, y, value, peak):
	basex, basey = map_to_img(x, y)
	peak = 0
	for dx in SPREAD_RANGE:
		for dy in SPREAD_RANGE:
			if basey + dy < 0 or basex + dx < 0: continue # No wrapping
			try: v = img[basey + dy][basex + dx]
			except IndexError: continue # Past edge? No dot needed
			if dx or dy:
				altx, alty = img_to_map(basex + dx, basey + dy)
				dist = (altx - x) ** 2 + (alty - y) ** 2
				if dist >= DECAY_RADIUS: continue # It's in the corner of the square, too far to be relevant.
				v += value * ((DECAY_RADIUS - dist) / DECAY_RADIUS) ** 0.5
				# print("%.3f %3d %d %d %.3f" % (dist, dx**2+ dy**2, dx, dy, ((DECAY_RADIUS - dist) / DECAY_RADIUS) ** 0.5))
			else: v += value
			img[basey + dy][basex + dx] = v
			peak = max(peak, v)
	return peak

finders = defaultdict(list)
def finder(key, desc):
	def deco(func):
		finders[key].append((func, desc))
		return func
	return deco

@finder("smokegrenade_detonate", "Smoke throws")
def smoke(params):
	return params[0], params[1], 1
@finder("flash_hit", "FB detonations") # Scored by opponents blinded
def flash_pop(params):
	if params[1] in ("Self", "Team"): return None
	return params[0], params[2], float(params[4])
@finder("flash_hit", "FB victims") # Ditto.
def flash_hit(params):
	if params[1] in ("Self", "Team"): return None
	return params[0], params[3], float(params[4])

images = defaultdict(lambda: [[0.0] * IMAGE_WIDTH for _ in range(IMAGE_HEIGHT)])
img_peaks = defaultdict(int)
img_descs = defaultdict(str)
with open("all_data.txt") as f:
	teams = { }
	for line in f:
		if line.startswith("match730_"):
			# New demo file, identified by file name
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
		for func, desc in finders[key]:
			who, where, value = func(params) or ('', '', 0)
			if not value: continue
			x, y, *_ = where.split(",") # Will have a z coordinate; may also have pitch and yaw.
			for teamtag in ("", "_" + teams[who]):
				fn = func.__name__ + "_" + who.split()[0] + teamtag
				img = images[fn]
				img_peaks[fn] = add_dot_to_image(img, float(x), float(y), value, img_peaks[fn])
				img_descs[fn] = desc + " - " + who.split()[0] + " - " + {"_C": "CT", "_T": "T", "": "All"}[teamtag]

with open("template.html") as t, open("heatmap.html", "w") as f:
	before, after = t.read().split("$$content$$")
	print(before, file=f)
	for fn, img in sorted(images.items()):
		generate_image(img, 0.875, img_peaks[fn], (0, 64, 0, 255), (240, 255, 240, 255)).save(fn + ".png")
		print(fn + ".png", img_peaks[fn])
		print("<li><label><input type=radio name=picker value=%s> %s</label></li>" % (fn, img_descs[fn]), file=f)
	print(after, file=f)
