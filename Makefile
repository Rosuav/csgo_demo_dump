all: de_dust2_radar.png all_data.txt

all_data.txt: searchdemos.py index.js ../.steam/steam/steamapps/common/Counter-Strike*Offensive/csgo/replays/*.dem
	python3 searchdemos.py | tee $@

de_dust2_radar.png: ../.steam/steam/steamapps/common/Counter-Strike*Offensive/csgo/resource/overviews/de_dust2_radar.dds
	convert "$<" $@
