import os
import subprocess
from glob import glob
for fn in sorted(glob("../.steam/steam/steamapps/common/Counter-Strike Global Offensive/csgo/replays/*.dem"))[::-1]:
	print(os.path.basename(fn), flush=True)
	subprocess.check_call(["node", "index.js", fn])
