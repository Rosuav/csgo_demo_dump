const fs = require("fs");
const demofile = require("demofile");

const fn = process.argv[2];
const data = fs.readFileSync(fn);
const demo = new demofile.DemoFile();

//Return a 'parser-safe' version of a string
//The resulting string will not have any newlines or colons in it.
function safe(s) {
	return s.replace(/[:\0-\x1f]/g, ".");
}

let current_round = 0;
demo.gameEvents.on("round_start", e => {
	if (demo.entities.gameRules.isWarmup) current_round = 0;
	else current_round = demo.entities.gameRules.roundsPlayed + 1;
});

demo.gameEvents.on("weapon_fire", e => {
	const player = demo.entities.getByUserId(e.userid);
	console.log(`weapon_fire:R${current_round}:${safe(player.name||e.userid)}:${e.weapon}`);
});
demo.parse(data);
