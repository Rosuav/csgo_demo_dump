/* Calculate damage and kills for each player against each player */
const fs = require("fs");
const demofile = require("demofile");

const fn = process.argv[2];
const data = fs.readFileSync(fn);
const demo = new demofile.DemoFile();

let current_round = 0;
let health = { }; //Map name to health. This assumes everyone has stable and unique names, which isn't true.
const total_damage = { }, kills = { };

demo.gameEvents.on("round_start", e => {
	if (demo.entities.gameRules.isWarmup) current_round = 0;
	else current_round = demo.entities.gameRules.roundsPlayed + 1;
	health = { }; demo.players.forEach(p => health[p.name] = 100);
	//if (current_round) console.log("Parsing round " + current_round + "...");
});

demo.gameEvents.on("player_hurt", e => {
	if (!current_round) return;
	const victim = demo.entities.getByUserId(e.userid);
	const attack = demo.entities.getByUserId(e.attacker);
	const key = (attack ? attack.name : "world") + " ==> " + (victim ? victim.name : "world");
	const dmg = Math.min(health[victim.name], e.dmg_health);
	if (!e.health) kills[key] = (kills[key]||0) + 1;
	total_damage[key] = (total_damage[key]||0) + dmg;
	health[victim.clientSlot] = e.health;
});

function pad(n) {n += ""; return "[" + "    ".slice(n.length) + n + "] ";}

function describe(mapping, desc) {
	Object.entries(mapping).sort((a, b) => (b[1] - a[1]) || a[0].localeCompare(b[0]))
		.forEach(([line, count]) => console.log(pad(count) + line.replace(" ==> ", desc)));
}

demo.on("end", e => {
	describe(kills, " killed ");
	describe(total_damage, " damaged ");
});

demo.parse(data);
