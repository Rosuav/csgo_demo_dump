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
const players_by_index = { };
const teams = "?STC"; // == Unknown, Spectator, Terrorist, CT
let stephen = -1, rosuav = -1;
demo.gameEvents.on("round_start", e => {
	if (demo.entities.gameRules.isWarmup) current_round = 0;
	else current_round = demo.entities.gameRules.roundsPlayed + 1;
	round_start_time = demo.currentTime;
	//Once we get into the game proper, report the participants. Note that the team shown
	//is the team that player *started* on; in the game history browser, it shows the team
	//that everyone *ended* on (as it's a match-end scoreboard), so they're inverted.
	if (current_round === 1) demo.players.forEach((p, i) => {
		if (p.steam64Id !== "0") console.log("player:" + i
			+ ":" + safe(p.steam64Id) + ":" + safe(p.name)
			+ ":" + p.clientSlot + ":" + teams[p.props.DT_BaseEntity.m_iTeamNum]
		);
		if (p.steam64Id === '76561198197864845') stephen = i;
		if (p.steam64Id === '76561198043731689') rosuav = i;
		players_by_index[p.index] = p;
	});
	if (current_round) report("round_start"); //Show the tick numbers of round starts (other than warmup)
});

let rosdead = false, first_kill = "E";
demo.gameEvents.on("round_freeze_end", e => {
	round_start_time = demo.currentTime;
	rosdead = false;
	first_kill = "E"; //Entry kill/death
});

demo.gameEvents.on("player_death", e => {
	if (!current_round) return; //Ignore warmup
	const victim = demo.entities.getByUserId(e.userid);
	const attack = demo.entities.getByUserId(e.attacker);
	/*
	//Special: Locate that one awesome moment where I called "go up mid" and Stephen found the guy who was trying to save!
	//match730_003435962081474511203_1366807403_171.dem round 14.
	if (victim && victim.clientSlot === rosuav) rosdead = true;
	else if (attack && attack.clientSlot === stephen && rosdead)
	{
		const v = victim.position.x ** 2 + victim.position.y ** 2; //Distance-squared from origin to victim
		const a = attack.position.x ** 2 + attack.position.y ** 2; //... and attacker
		if (v < 5e5 && a < 5e5) report("stephenkill", e.weapon, `${a|0}-${v|0}`, location(victim));
		//console.log(e)
	}
	*/
	let tag, who;
	if (attack && interesting_steamid[attack.steam64Id]) {tag = "kill"; who = attack;}
	if (victim && interesting_steamid[victim.steam64Id]) {tag = "death"; who = victim;}
	if (tag) {
		//This shows the weapon I was killed with, but not the weapon I was killed holding.
		//True analysis should include (a) what weapon I started the round with, (b) what primary
		//I possessed as I died, (c) which weapon was currently active, and (d) whether I'd just
		//stupidly grabbed a new weapon. Also maybe (e) whether the weapon was empty?
		report(tag, who.name||who.userid, first_kill + (e.headshot ? "H" : ""), e.weapon, location(attack), location(victim));
	}
	first_kill = ""; //The first kill of the round gets a flag, absent if not first
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
	//Possibly demo.gameEvents.once("tick", ...) or something?
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

demo.gameEvents.on("cs_win_panel_round", e => {
	const player = players_by_index[e.funfact_player];
	report("round_end", e.funfact_token, player ? player.name : "", ""+e.funfact_data1, ""+e.funfact_data2, ""+e.funfact_data3);
});

const mvp_reason_desc = [undefined,
	"most eliminations",
	"planting the bomb",
	"defusing the bomb",
];
demo.gameEvents.on("round_mvp", e => {
	const player = demo.entities.getByUserId(e.userid);
	//There's an associated e.value, but it doesn't seem to ever carry any information.
	report("round_mvp", player ? player.name : "", mvp_reason_desc[e.reason] || "reason code "+e.reason);
});

demo.on("end", e => {
	demo.players.forEach((p, i) => {
		if (p.steam64Id === "0") return;
		let kills = 0, assists = 0, deaths = 0, objectives = 0, eqval_by_kill = 0, save_kills = 0, lightbuy_kills = 0;
		for (let r = 0; r < current_round; r++) {
			const k = ("000" + r).slice(-3);
			const frags = p.props.m_iMatchStats_Kills[k];
			kills += frags;
			assists += p.props.m_iMatchStats_Assists[k];
			deaths += p.props.m_iMatchStats_Deaths[k];
			objectives += p.props.m_iMatchStats_Objective[k];
			if (frags) {
				let eq = p.props.m_iMatchStats_EquipmentValue[k];
				eqval_by_kill += eq * frags;
				//TODO: Filter down to just kills when the other team was on a full buy
				if (r != 0 && r != 15 && eq < 1000) save_kills += frags;
				if (r != 0 && r != 15 && eq < 2900) lightbuy_kills += frags; //I'd set it to 3000 but an AK with a starting pistol counts as a full buy in silvers
			}
		}
		console.log("player:" + i
			+ ":" + safe(p.steam64Id) + ":" + safe(p.name)
			+ ":" + p.clientSlot + ":" + teams[p.props.DT_BaseEntity.m_iTeamNum]
			+ ":" + kills + ":" + assists + ":" + deaths + ":" + objectives
			+ ":S" + save_kills + ":L" + lightbuy_kills
			+ ":" + (kills ? Math.floor(eqval_by_kill / kills) : 0)
		);
	});
	//console.log(demo.players[0]);
});

demo.parse(data);

/*
Other stats to try to find or calculate:
- Score/round
- K/R
- K/D
- Entry K/D (filter to those with the "E" flag)
- ADR
- Whether the match had blatant cheaters in it (so I can calculate all those stats for the cheater-free matches)
*/
