all: de_dust2_radar.png demodata.json

de_dust2_radar.png: ../.steam/steam/steamapps/common/Counter-Strike*Offensive/csgo/resource/overviews/de_dust2_radar.dds
	convert "$<" $@

demodata.json: searchdemos.py index.js ../.steam/steam/steamapps/common/Counter-Strike*Offensive/csgo/replays/*.dem
	python3 searchdemos.py
