import hashlib
import json
import os
import subprocess
from glob import glob

# If code changes, we need to fully regenerate everything.
with open("searchdemos.py", "rb") as py, open("index.js", "rb") as js:
	codehash = hashlib.sha256(py.read() + js.read()).hexdigest()
data = None
try:
	with open("demodata.json") as f:
		data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError): pass
if not isinstance(data, dict) or data["codehash"] != codehash:
	print("Starting fresh.")
	data = {"codehash": codehash}

try:
	for fn in sorted(glob("../.steam/steam/steamapps/common/Counter-Strike Global Offensive/csgo/replays/*.dem"))[::-1]:
		base = os.path.basename(fn)
		if base in data: continue
		print(base, flush=True)
		proc = subprocess.run(["node", "index.js", fn], capture_output=True, check=True)
		info = [line.strip().decode("UTF-8") for line in proc.stdout.split(b"\n") if line.strip()]
		# The demo file doesn't seem to include its date/time, although I'm sure it ought
		# to be there somewhere. As a substitute, grab the file's mtime.
		info.insert(0, "date:%d" % os.stat(fn).st_mtime)
		data[base] = info
except KeyboardInterrupt:
	print("Halting early")

with open("demodata.json", "w") as f:
	json.dump(data, f, indent=2)
