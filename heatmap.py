import png # pip install pypng

data = [
    [745.2218627929688,808.1373901367188,1],
    [741.4943237304688,775.325927734375,1],
    [757.3713989257812,806.7517700195312,1],
    [-300.1320495605469,1425.9727783203125,1],
    [-1845.8055419921875,2091.180419921875,1],
    [-289.85308837890625,1429.4222412109375,1],
    [-306.8935241699219,1434.9525146484375,1],
    [-287.78253173828125,1439.9078369140625,1],
]

# (0,0) on the image should correspond to (MAP_XMIN, MAP_YMIN)
# If the coordinates need to be inverted, set (eg) XMIN to a high
# number and XMAX to a low number. Fine-tune to align the heatmap.
IMAGE_WIDTH = IMAGE_HEIGHT = 1024
MAP_XMIN = -2500; MAP_YMIN = 3400; MAP_XMAX = 2100; MAP_YMAX = -1200
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

def inverse_squares(basex, basey, data):
	# Calculate the distance-squared to each data point.
	tot = 0
	for x, y, value in data:
		dist = (x-basex) ** 2 + (y-basey) ** 2
		if dist >= DECAY_RANGE2: continue
		print(basex, basey, dist ** 0.5)
		tot += value * (DECAY_RANGE2 - dist) ** 0.5 / DECAY_RANGE
	return tot

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
img, peak = build_map(data)
#for row in img:
#	print(" ".join(format(x, ".1f") if x >= 1.0 else "---" for x in row))
#print(peak)
generate_image(img, 1.0, peak, (0, 64, 0, 255), (255, 255, 255, 255)).save("output.png")
