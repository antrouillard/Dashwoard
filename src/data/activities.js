/**
 * Schedule of weekly WoW activities for TWW Season 1 (2026).
 *
 * Each week has:
 *  - id        : unique slug
 *  - title     : display name
 *  - startDate : ISO date string (Monday / Wednesday of the reset) – inclusive
 *  - endDate   : ISO date string – inclusive  (day before next week starts)
 *  - note      : optional header note (e.g. crest-spending warning)
 *  - tasks     : array of task objects
 *
 * Task fields:
 *  - id        : unique string (used as localStorage key suffix)
 *  - label     : human-readable task description
 *  - important : boolean – displayed more prominently
 *  - tracking  : optional tracking info string (e.g. crest counters)
 *  - note      : optional italic sub-note
 */

export const WEEKS = [
  {
    id: "early-access",
    title: "Early Access",
    subtitle: "Feb 26 – Mar 2 · Pay to Win",
    startDate: "2026-02-26",
    endDate: "2026-03-02",
    note: "Do NOT spend any Crests until told to do so",
    tasks: [
      {
        id: "ea-1",
        label: "Level characters to 90 — DMF opens Sunday for +10% XP",
        important: true,
      },
      {
        id: "ea-2",
        label:
          "After Sunday, use DMF buff to raise renowns (see Week 1 guide)",
      },
      {
        id: "ea-3",
        label:
          "Complete weekly events if available (TBD – will add as we get them)",
      },
      {
        id: "ea-4",
        label:
          "If Prey can be upgraded, do so — Nightmare Preys might give Champion pieces",
      },
    ],
  },
  {
    id: "preseason-w1",
    title: "Week 1",
    subtitle: "Mar 3 · Pre-Season · M0s open",
    startDate: "2026-03-03",
    endDate: "2026-03-09",
    note: "Do NOT spend any Crests until told to do so",
    tasks: [
      {
        id: "psw1-1",
        label: "Raise The Singularity renown to rank 7 → 1/6 Champion trinket",
        important: true,
      },
      {
        id: "psw1-2",
        label: "Raise Hara'ti renown to rank 8 → 1/6 Champion belt",
        important: true,
      },
      {
        id: "psw1-3",
        label: "Raise Silvermoon renown to rank 9 → 1/6 Champion helm",
        important: true,
      },
      {
        id: "psw1-4",
        label: "Raise Amani Tribe renown to rank 9 → 1/6 Champion necklace",
        important: true,
      },
      {
        id: "psw1-5",
        label: "Unlock Delves through tier 8 (tier 11 if available)",
      },
      {
        id: "psw1-6",
        label:
          "Complete weekly events if available (TBD – will add as we get them)",
      },
      {
        id: "psw1-7",
        label:
          "If Prey gives useful rewards, do Prey (might give Champion pieces on Nightmare)",
      },
      {
        id: "psw1-8",
        label: "Do world quests that give gear upgrades",
      },
      {
        id: "psw1-9",
        label:
          "Complete a World Tour of M0 dungeons — rewards Veteran ilvl (do NOT upgrade yet)",
        important: true,
      },
      {
        id: "psw1-10",
        label: "Queue for Heroic Dungeons for remaining slots",
      },
    ],
  },
  {
    id: "preseason-w2",
    title: "Week 2",
    subtitle: "Mar 10 · Pre-Season · M0s",
    startDate: "2026-03-10",
    endDate: "2026-03-16",
    note: "Do NOT spend any Crests until told to do so",
    tasks: [
      {
        id: "psw2-1",
        label: "Unlock Delves through tier 8 (tier 11 if available)",
      },
      {
        id: "psw2-2",
        label:
          "Complete weekly events if available (TBD – will add as we get them)",
      },
      {
        id: "psw2-3",
        label:
          "If Prey gives useful rewards, do Prey (might give Champion pieces on Nightmare)",
      },
      {
        id: "psw2-4",
        label: "Do world quests that give gear upgrades",
      },
      {
        id: "psw2-5",
        label:
          "Complete a World Tour of M0 dungeons — rewards Veteran ilvl (do NOT upgrade)",
        important: true,
      },
      {
        id: "psw2-6",
        label: "Queue for Heroic Dungeons for remaining slots",
      },
      {
        id: "psw2-7",
        label:
          "If you raid Tuesday Mar 17, craft beforehand — see doc for details",
        note: "Preparation for Season 1 Week 1 raid",
      },
    ],
  },
  {
    id: "s1-w1",
    title: "Week 3",
    subtitle: "Mar 17 · S1 · Heroic Week",
    startDate: "2026-03-17",
    endDate: "2026-03-23",
    note: "Do NOT spend Heroic or Mythic Crests",
    tasks: [
      {
        id: "s1w1-1",
        label: "Do LFR for tier pieces (check guide for why)",
        important: true,
      },
      {
        id: "s1w1-2",
        label: "Complete a World Tour of M0 dungeons — rewards Champion ilvl",
        important: true,
      },
      {
        id: "s1w1-3",
        label: "Kill World Boss for Champion ilvl",
      },
      {
        id: "s1w1-4",
        label:
          "Do high-level bountiful Delves with coffer keys — use map if possible",
      },
      {
        id: "s1w1-5",
        label:
          "If Prey gives useful rewards, do Prey (might give Champion pieces on Nightmare)",
      },
      {
        id: "s1w1-6",
        label: "Complete PvP quest for guaranteed Hero neck / ring",
      },
      {
        id: "s1w1-7",
        label:
          "Before raid: craft 2× 246 ilvl pieces + 2× embellishments on weak slots — use 160 Veteran Crests",
        important: true,
      },
      {
        id: "s1w1-8",
        label:
          "Before raid: spend ALL Veteran and Champion Crests upgrading everything",
        important: true,
      },
      {
        id: "s1w1-9",
        label: "Complete your raids",
        important: true,
      },
    ],
    tracking: "Crests: 0 / 100 Heroic · 0 / 100 Mythic",
  },
  {
    id: "s1-w2",
    title: "Week 4",
    subtitle: "Mar 24 · S1 · Mythic Week — M+ Opens",
    startDate: "2026-03-24",
    endDate: "2026-03-30",
    tasks: [
      {
        id: "s1w2-1",
        label: "Do LFR for tier pieces (check guide for why)",
      },
      {
        id: "s1w2-2",
        label: "Kill World Boss for Champion ilvl",
      },
      {
        id: "s1w2-3",
        label:
          "Do high-level bountiful Delves with coffer keys — use map if possible",
      },
      {
        id: "s1w2-4",
        label: "Do at least one t11 Delve to get Cracked Keystone Quest",
        note: "Even if you skip Delves this week",
      },
      {
        id: "s1w2-5",
        label: "Farm +10s for 266 gear in every slot",
        important: true,
      },
      {
        id: "s1w2-6",
        label: "1H crafted note — check guide (ignore if you don't dual-wield)",
      },
      {
        id: "s1w2-7",
        label: "Full Clear Normal and Heroic",
        important: true,
      },
      {
        id: "s1w2-8",
        label: "Before Mythic raid: upgrade 11× 3/6 Hero items once each",
        important: true,
      },
      {
        id: "s1w2-9",
        label: "Enjoy Mythic Progression! 🎉",
      },
      {
        id: "s1w2-10",
        label:
          "If lucky and got a Myth track item, jump to next week's upgrade advice for it",
        note: "Mythic only",
      },
    ],
    tracking: "Crests: 220 / 220 Heroic · 0 / 220 Mythic",
    endingIlvl: "4×266 · 11×269",
  },
  {
    id: "s1-w3",
    title: "Week 5",
    subtitle: "Mar 31 · S1 · Final Raid Opens",
    startDate: "2026-03-31",
    endDate: "2026-04-06",
    tasks: [
      {
        id: "s1w3-1",
        label: "Open vault (272+ Myth item) — upgrade AFTER crafting",
        important: true,
      },
      {
        id: "s1w3-2",
        label: "Craft 2H Mythic weapon (5/6 → 285) — see note in text guide",
        important: true,
      },
      {
        id: "s1w3-3",
        label:
          "If no 4-piece set bonus yet, do LFR for tier pieces (check guide)",
      },
      {
        id: "s1w3-4",
        label: "Farm +12s for vault + Crests",
        important: true,
      },
      {
        id: "s1w3-5",
        label:
          "Heroic: upgrade 2× 4/6 269 items to 6/6 276 — costs 80 Heroic Crests",
      },
      {
        id: "s1w3-6",
        label:
          "Mythic: if vault item was 1/6, upgrade its Heroic counterpart to 6/6 (20 Heroic Crests) then upgrade vault item 1/6→6/6 289 (80 Myth Crests)",
        note: "Mythic players",
      },
      {
        id: "s1w3-7",
        label: "Full Clear Normal, Heroic, + as much Mythic as possible",
        important: true,
      },
      {
        id: "s1w3-8",
        label:
          "If you got a 2nd Myth track item, jump to next week's upgrade advice for it",
        note: "Mythic only",
      },
    ],
    tracking: "Crests: 320 / 320 Heroic · 160 / 320 Mythic",
    endingIlvl: "3×266 · 8×269 · 2×276H · 1×285(crafted) · 1×289",
  },
  {
    id: "s1-w4",
    title: "Week 6",
    subtitle: "Apr 7 · S1",
    startDate: "2026-04-07",
    endDate: "2026-04-13",
    tasks: [
      {
        id: "s1w4-1",
        label: "Open vault (272+ Myth item)",
        important: true,
      },
      {
        id: "s1w4-2",
        label: "Farm +12s for vault + Crests",
        important: true,
      },
      {
        id: "s1w4-3",
        label:
          "Heroic: upgrade 2× 4/6 269 items to 6/6 276 — costs 80 Heroic Crests",
      },
      {
        id: "s1w4-4",
        label:
          "Mythic: if vault item was 1/6, upgrade Heroic counterpart to 6/6 (20 Heroic Crests) then upgrade 1/6→6/6 289 (80 Myth Crests)",
        note: "Mythic players",
      },
      {
        id: "s1w4-5",
        label:
          "Mythic: upgrade your raid drop from 2/6 275 → 6/6 289 — costs 80 Myth Crests",
        note: "Mythic players",
      },
    ],
    tracking: "Crests: 420 / 400 Heroic · 320 / 420 Mythic",
    endingIlvl: "2×266 · 5×269 · 4×276H · 1×285(crafted) · 3×289",
  },
  {
    id: "s1-w5",
    title: "Week 7",
    subtitle: "Apr 14 · S1",
    startDate: "2026-04-14",
    endDate: "2026-04-20",
    tasks: [
      {
        id: "s1w5-1",
        label: "Open vault (272+ Myth item)",
        important: true,
      },
      {
        id: "s1w5-2",
        label: "Farm +12s for vault + Crests",
        important: true,
      },
      {
        id: "s1w5-3",
        label:
          "Craft 2nd embellishment at 285 ilvl Mythic — costs 80 Myth Crests",
        important: true,
      },
      {
        id: "s1w5-4",
        label:
          "Heroic: upgrade 2× 4/6 269 items to 6/6 276 — costs 80 Heroic Crests",
      },
      {
        id: "s1w5-5",
        label:
          "Mythic: if vault item was 1/6, upgrade Heroic counterpart to 6/6 (20 Heroic Crests) then upgrade 1/6→6/6 289 (80 Myth Crests)",
        note: "Mythic players",
      },
    ],
    tracking: "Crests: 520 / 520 Heroic · 480 / 520 Mythic",
    endingIlvl: "1×266 · 2×269 · 6×276H · 2×285(crafted) · 4×289",
  },
  {
    id: "s1-w6",
    title: "Week 8",
    subtitle: "Apr 21 · S1 · Done with Heroic Crests",
    startDate: "2026-04-21",
    endDate: "2026-04-27",
    tasks: [
      {
        id: "s1w6-1",
        label: "Open vault (272+ Myth item)",
        important: true,
      },
      {
        id: "s1w6-2",
        label: "Farm +12s for vault + Crests",
        important: true,
      },
      {
        id: "s1w6-3",
        label:
          "Heroic: upgrade your LAST 4/6 269 item to 6/6 276 — costs 40 Heroic Crests",
      },
      {
        id: "s1w6-4",
        label:
          "Mythic: if vault item was 1/6, upgrade Heroic counterpart to 6/6 (20 Heroic Crests) then upgrade 1/6→6/6 289 (80 Myth Crests)",
        note: "Mythic players",
      },
      {
        id: "s1w6-5",
        label:
          "Mythic: upgrade your raid drop from 2/6 275 → 6/6 289 — costs 80 Myth Crests",
        note: "Mythic players",
      },
    ],
    tracking: "Crests: 560 / 620 Heroic · 620 / 620 Mythic",
    endingIlvl: "7×276H · 2×285(crafted) · 1×285 · 5×289",
  },
  {
    id: "s1-w7",
    title: "Week 9+",
    subtitle: "Apr 28+ · S1",
    startDate: "2026-04-28",
    endDate: null, // open-ended
    tasks: [
      {
        id: "s1w7-1",
        label:
          "Do not craft if you can get vault items higher than 1/6",
        important: true,
      },
      {
        id: "s1w7-2",
        label:
          "Upgrade Mythic items as you get them — prioritise jumping to 289 (+4 jump)",
        important: true,
      },
      {
        id: "s1w7-3",
        label: "Plan for possible 1H + crafted off-hand swap",
      },
      {
        id: "s1w7-4",
        label: "Enjoy Blizzard's much better upgrade system! 🎉",
      },
    ],
  },
];

/**
 * Returns the week object that covers today's date,
 * or null if today is before the schedule starts.
 */
export function getCurrentWeek(today = new Date()) {
  const todayStr = today.toISOString().split("T")[0];

  for (const week of WEEKS) {
    if (todayStr < week.startDate) continue;
    if (week.endDate === null) return week; // open-ended final week
    if (todayStr <= week.endDate) return week;
  }

  // Before the schedule begins
  return null;
}

/**
 * Returns all weeks INCLUDING and AFTER the current week.
 */
export function getUpcomingWeeks(today = new Date()) {
  const current = getCurrentWeek(today);
  if (!current) return WEEKS;
  const idx = WEEKS.findIndex((w) => w.id === current.id);
  return WEEKS.slice(idx);
}
