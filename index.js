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

const interesting_steamid = {"76561198197864845": "Stephen", "76561198043731689": "Rosuav"};
const teams = "?STC"; // == Unknown, Spectator, Terrorist, CT
let stephen = -1, rosuav = -1;
demo.gameEvents.on("round_start", e => {
	if (demo.entities.gameRules.isWarmup) current_round = 0;
	else current_round = demo.entities.gameRules.roundsPlayed + 1;
	round_start_time = demo.currentTime;
	//Once we get into the game proper, report the participants.
	if (current_round === 1) demo.players.forEach((p, i) => {
		if (p.steam64Id !== "0") console.log("player:" + i + ":" + safe(p.steam64Id) + ":" + safe(p.name));
		if (p.steam64Id === '76561198197864845') stephen = i;
		if (p.steam64Id === '76561198043731689') rosuav = i;
	});
	if (current_round) report("round_start"); //Show the tick numbers of round starts (other than warmup)
});

let rosdead = false;
demo.gameEvents.on("round_freeze_end", e => {
	round_start_time = demo.currentTime;
	rosdead = false;
});

//Special: Locate that one awesome moment where I called "go up mid" and Stephen found the guy who was trying to save!
//match730_003435962081474511203_1366807403_171.dem round 14.
demo.gameEvents.on("player_death", e => {
	const victim = demo.entities.getByUserId(e.userid);
	const attack = demo.entities.getByUserId(e.attacker);
	if (victim && victim.clientSlot === rosuav) rosdead = true;
	else if (attack && attack.clientSlot === stephen && rosdead)
	{
		const v = victim.position.x ** 2 + victim.position.y ** 2; //Distance-squared from origin to victim
		const a = attack.position.x ** 2 + attack.position.y ** 2; //... and attacker
		if (v < 5e5 && a < 5e5) report("stephenkill", e.weapon, `${a|0}-${v|0}`, location(victim));
		//console.log(e)
	}
});

demo.gameEvents.on("weapon_fire", e => {
	const player = demo.entities.getByUserId(e.userid);
	//report("weapon_fire", player.name||e.userid, e.weapon, location(player));
});

demo.gameEvents.on("smokegrenade_detonate", e => {
	const player = demo.entities.getByUserId(e.userid);
	if (!interesting_steamid[player.steam64Id]) return;
	report("smokegrenade_detonate", player.name||e.userid, teams[player.props.DT_BaseEntity.m_iTeamNum], `${e.x},${e.y},${e.z}`);
});

let last_flash = "0,0,0";
demo.gameEvents.on("flashbang_detonate", e => {
	//TODO: Count how many people got caught by it
	//The player_blind events happen *after* the detonation event.
	const player = demo.entities.getByUserId(e.userid);
	if (!interesting_steamid[player.steam64Id]) return;
	report("flashbang_detonate", player.name||e.userid, last_flash = `${e.x},${e.y},${e.z}`, ""+player.props.DT_CSPlayer.m_flFlashDuration);
});

demo.gameEvents.on("player_blind", e => {
	const victim = demo.entities.getByUserId(e.userid);
	const attack = demo.entities.getByUserId(e.attacker);
	if (!interesting_steamid[attack.steam64Id]) return;
	report("flash_hit", attack.name||e.attacker,
		//"CvC" or "TvT" is a team flash. "CvT" means CT flashed T, "TvC" means T flashed CT.
		e.userid === e.attacker ? "Self" : teams[attack.props.DT_BaseEntity.m_iTeamNum] + "v" + teams[victim.props.DT_BaseEntity.m_iTeamNum],
		last_flash, location(victim), ""+e.blind_duration,
	);
});

demo.parse(data);
