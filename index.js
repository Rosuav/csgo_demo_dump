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

let current_round = 0, round_start_time = 0;

//Report something interesting
//Format: thing:<tick>:R<round>:<time within round>:arg:arg:arg:arg
//Within-round time counts from the time the round started or freeze time ended.
//All args are passed through safe().
function report(key) {
	let msg = key + ":" + demo.currentTick + ":R" + current_round + ":" + (demo.currentTime - round_start_time);
	for (let i=1; i<arguments.length; ++i) msg += ":" + safe(arguments[i]);
	console.log(msg);
}

//Return the player's location in a consistent and compact way
function location(player) {
	if (!player) return "";
	const pos = player.position, eye = player.eyeAngles;
	return [pos.x, pos.y, pos.z, eye.pitch, eye.yaw].map(n => n.toFixed(2)).join(",")
}

demo.gameEvents.on("round_start", e => {
	if (demo.entities.gameRules.isWarmup) current_round = 0;
	else current_round = demo.entities.gameRules.roundsPlayed + 1;
	round_start_time = demo.currentTime;
});

demo.gameEvents.on("round_freeze_end", e => {
	round_start_time = demo.currentTime;
});

demo.gameEvents.on("weapon_fire", e => {
	const player = demo.entities.getByUserId(e.userid);
	report("weapon_fire", player.name||e.userid, e.weapon, location(player));
});
demo.parse(data);
