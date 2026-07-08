# TODO — social-poster tag overhaul (July 2026)

Follow-ups from the July 2026 tag research
([research](config/tag-research-2026-07.md) · [changes applied](config/tag-changes-2026-07.md) ·
[theme research](config/tag-research-themes-2026-07.md) · [gallery analysis](analysis/)).

## New PhotoTypes (from gallery clustering + theme research)

- [ ] Decide which of the 12 candidate PhotoTypes to add to `tags.json`
      (recommended tags per theme in the theme research doc): Mountains, Forest,
      Water, Fog, Winter, Dogs, Night, Hiking, StreetArt, Desert, Food, RoadTrip.
- [ ] Add matching Lightroom keywords under `cameracoffeewander|PhotoType|<Name>`
      for whichever are adopted.
- [ ] Dogs features are submission-based, not tag-based: email your best 2-3 dog
      shots to dogs.instagram@gmail.com (@dogsofinstagram, 5M).
- [ ] In-app: spend 10 min on #mountainphotography / #forestphotography /
      #desertphotography looking for mid-size (50-500K) curator accounts web
      search can't surface; same for #dogsofbluesky on Bluesky.
- [ ] Verify @moodygrams / @nightphotography exact feature mechanics in-app
      (bio/pinned post) before relying on them.

## Lightroom — add 20 keywords

Keyword names must match `tags.json` keys exactly (case-sensitive, no spaces).
All nested under the `cameracoffeewander` root; nothing existing was renamed.

- [ ] `Place > USA > Alaska > State`
- [ ] `Place > USA > Wyoming > State`
- [ ] `Place > USA > Idaho > State`
- [ ] `Place > USA > Oregon > State`
- [ ] `Place > USA > Washington > State`
- [ ] `Place > Canada > Yukon > Province`
- [ ] `Place > Canada > BritishColumbia > Province` (one word)
- [ ] `Place > Canada > Alberta > Province`
- [ ] `Place > NationalPark > Denali`
- [ ] `Place > NationalPark > Katmai`
- [ ] `Place > NationalPark > KenaiFjords`
- [ ] `Place > NationalPark > WrangellStElias`
- [ ] `Place > NationalPark > Yellowstone`
- [ ] `Place > NationalPark > GrandTeton`
- [ ] `Place > NationalPark > Olympic`
- [ ] `Place > NationalPark > Kootenay`
- [ ] `Place > NationalPark > Jasper`
- [ ] `Place > NationalPark > Yoho`
- [ ] `Place > NationalPark > GlacierCanada` (existing `Glacier` stays = Montana)
- [ ] `SocialEvent > WorldCup2026`

## In-app verification (couldn't be confirmed from the web)

Open Instagram and check each is alive / still featuring; drop from `tags.json` if dead:

- [ ] `#mundusmag` (Portrait priority)
- [ ] `#shadows_magazine` (Shadows priority)
- [ ] `@milkyway_nightscape` / `#milkyway_nightscape_` (Stars priority)
- [ ] `#dpsp_rainshots` (Storms general)
- [ ] `@only.in.utah`, `@visitmoab` / `#visitmoab`, `#utahscanyoncountry` (Utah priority)
- [ ] `@vermonttourism` (Vermont)
- [ ] `@banff.national.park` (fan account — Parks Canada is now the primary)
- [ ] `@mexico_fotografos` recency (75K, bio invites the tag, but recent activity was behind the login wall)
- [ ] Confirm `@analogsunrise` is really dead (already removed — re-add if wrong)

## Bluesky actions (one-time)

- [ ] Comment on the pinned post of the **Top Nature Photography** feed
      (@nickchillphoto.com) to request contributor status — allowlist feed, triggers
      #landscape/#wildlife/#astro/#nature; requires alt text, no AI.
- [ ] Engage/follow **@bluesky.photography** (runs the curated Landscapes feed,
      active; selection is manual).
- [ ] Add alt text to every Bluesky photo post (several curated feeds require it) —
      consider making this a publisher feature.
- [ ] Adopt the analog caption convention on Bluesky film posts:
      `📷 <camera> / 🎞️ <film stock>` lines (keyword feeds match on it).

## Known gaps from the research (July 2026)

- [ ] **Hashtag volume is deprioritized on Instagram (2026):** Mosseri has said
      hashtags don't drive reach; posts with >5 tags may be *deprioritized*;
      hashtag-follows were removed; caption keywords now drive search discovery.
      Decide whether to cut `INSTAGRAM_TAG_LIMIT` from 30 to ~5 (priority hubs
      first) and invest in descriptive keyword-rich captions + alt text instead.
      The feature-hub strategy (getting reposted) is unaffected.
- [ ] **No Bluesky 300-char handling:** publisher doesn't enforce the limit —
      caption + big tag lists can exceed it. Add truncation/tag-budget logic.
- [ ] **No feedback loop:** nothing records whether a hub ever features a post or
      which tag sets correlate with engagement. Consider a simple "featured by"
      log + per-post engagement snapshot so next year's audit isn't guesswork.
- [ ] **Geotags not used:** Instagram location tags drive local discovery
      (CDMX especially); publisher doesn't set them.
- [ ] **Contests are an unexplored feature pipeline:** Cuartoscuro Concurso
      Nacional (Mexican residents 2+ yrs eligible — 2026 closed Mar 30, watch for
      2027; @cuartoscuromex is THE Mexican photojournalism institution — follow/tag
      for CDMX street/documentary work), Banff Mountain Photo Essay + Signature
      Image Search, National Park Photo Contest (Tamron), AlaskaTravel.com photo
      contest, SkyPixel, Lomography Awards, Ilford annual. Build a deadlines list.
- [ ] **Bluesky depth:** only ~5 of 1,300+ photography feeds verified; no
      starter-pack/follow-graph strategy researched.
- [ ] Stills-only strategy: IG reach in 2026 skews heavily to Reels — out of
      social-poster's scope, but it caps expectations for static-photo growth.

## Process / recurring

- [ ] Ilford **#fridayfavourites** rotates a weekly theme — check
      ilfordphoto.com/blog for the current theme tag before posting Ilford/Kentmere shots.
- [ ] NatGeo Your Shot monthly themed challenges use rotating tags
      (e.g. #NatGeoYourShotOurHOME) — worth checking when a photo fits the theme.
      Rules: public account, photo <6 months old, no AI/heavy manipulation.
- [ ] Decide on Utah's `#YesVisitUtah` permission flow — replying grants a
      perpetual, transferable license incl. paid ads. Only reply if OK with that.
- [ ] Prune WorldCup2026 spike tags (`#WeAre26`, `#Somos26`, `#SomosLeyendas`)
      once the tournament buzz dies (~Sept 2026); keep `#FIFAWorldCup`,
      `#EstadioAzteca`, `#Mundial2026`.
- [ ] Drone work: enter DJI's annual **SkyPixel** contest (skypixel.com) — that's
      where DJI actually features photographers, not Instagram tags.
- [ ] Re-run a staleness audit ~yearly; small feature hubs die often.
