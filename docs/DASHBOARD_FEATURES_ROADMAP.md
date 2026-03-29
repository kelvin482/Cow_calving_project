# Dashboard Features Roadmap

This roadmap captures planning direction and future ideas. It should not be
read as a guarantee that every item is already implemented in the codebase.

This document captures the simplified, hackathon-ready dashboard direction for
the project.

The goal is to keep the product:
- easy for beginners and farmers to understand
- professional enough for a hackathon demo
- focused on working features instead of feature overload

## Product Rule

Keep the interface simple.

- Farmers should not see technical system fields
- Vets should see only the information needed to act
- Extra detail should live behind a clear link or button

Examples of technical fields that should stay hidden from users:
- latitude
- longitude
- location source
- raw coordinate values

## New Hackathon Goal: Reproductive Management For Smallholder Dairy Farmers

The project should also solve a practical reproductive management gap for
smallholder dairy farmers in rural and low-resource settings.

The goal is not to build a full farm ERP.

The goal is to help farmers answer a few high-value questions clearly:
- is this cow likely in heat now?
- when is the best insemination window?
- where can I get affordable insemination help?
- did conception likely happen or is follow-up needed?
- when should I dry off and change pregnancy care?

For the hackathon, this should become one of the clearest product stories:

`Help a farmer move from reproductive uncertainty to the right next action.`

### Updated hackathon product goal

The strongest product story should now be:

`Register a cow, request insemination if needed, track reproductive progress, and prepare for calving with the right follow-up at the right time.`

This keeps the project practical and easy to demo because it connects:
- cow registration
- insemination access
- veterinary follow-up
- pregnancy and calving tracking
- future AI guidance

### Additional hackathon product goal: Track Maziwa

The project should also help farmers understand milk productivity in a way that
is simple and useful day to day.

The strongest milk story should be:

`Record daily milk for each cow, see how production is changing, and use the trend to decide when to follow up.`

This should support:
- daily milk tracking per cow
- simple cow drill-down
- a visible productivity curve
- better follow-up when production drops unexpectedly
- future AI support around productivity changes

## Hackathon-Ready Vet Dashboard Structure

The vet dashboard should stay focused on five main pages:

1. `Overview`
2. `Active Case`
3. `Farm Map`
4. `My Farms`
5. `Medical Records`

Support pages can still exist, but they should not crowd the main navigation.

Examples:
- schedule
- telehealth
- diagnosis
- prescriptions
- labs

These should be opened only when needed from links or action buttons.

## Main Dashboard Principle

The homepage should answer one question:

`What needs my attention right now?`

The homepage should stay light and should mainly show:
- compact stats
- urgent cases
- today's schedule
- links to deeper workflows

## Farmer Dashboard Improvement Roadmap

The farmer dashboard should feel simpler than the vet dashboard.

It should help a beginner farmer:
- see what matters today
- open the right next page
- avoid getting lost in too many cards

### Farmer overview structure

The farmer home should show only:
- compact summary counts
- cows due soon
- recent alerts
- a few clear quick actions
- links to deeper pages for the rest

### Farmer design direction

The farmer dashboard should borrow the same clean visual language as the vet
dashboard:
- one calm sidebar
- one simple header
- compact summary cards
- two main action lists
- one small quick-links area

This keeps the project consistent without making the farmer home heavy.

### What should move off the homepage

Do not keep these as large homepage sections:
- long account setup panels
- too many roadmap cards
- repeated explanation text
- detailed animal records
- full reports content

These should live behind dedicated pages instead:
- `My herd`
- `Alerts`
- `Reports`

### Farmer page rules

- The page should feel calm and easy to scan
- Important work should appear first
- Every section should support a real next action
- Extra information should be opened only when needed

### Farmer build order

1. simplify the overview arrangement
2. keep herd records on the herd page
3. keep alert follow-up on the alerts page
4. keep trends on the reports page
5. add farm location flow only after the simple dashboard works well

## Simplified Farmer Process System

The farmer dashboard should behave like a guided process, not a collection of
many unrelated features.

That means the farmer should be able to move through one simple operational
flow:

1. know which cow needs attention
2. understand the current stage
3. see the next action
4. ask for help or record follow-up

This is better than building many separate cards with no clear order.

### The farmer process should feel like this

- calm
- guided
- easy to scan
- action-first
- beginner-friendly

### Recommended farmer workflow

Use the current dashboard pages as one connected process:

1. `Overview`
- show what needs attention today
- show the process stages clearly
- highlight only the next important action

2. `My herd`
- show each cow inside the same process structure
- keep timeline, status, and next action together
- avoid mixing production detail with urgent reproductive follow-up

3. `Alerts`
- show only exceptions, missed steps, and urgent follow-up
- every alert must point to one next action

4. `Reports`
- keep trends and summary review here
- do not use reports as the main working page

### Suggested farmer process stages

For the hackathon, keep the workflow short:

1. `Watch`
- track heat signs, dates, and due windows

2. `Decide`
- judge whether the cow needs monitoring, insemination support, or calving preparation

3. `Act`
- request support, prepare the pen, or follow the next checklist step

4. `Follow up`
- confirm outcome, record what happened, and prepare the next cycle

### Design rule for the farmer dashboard

- one strong process section on the overview
- one workflow page for cow-level detail
- one alert page for exceptions
- one report page for trends

Avoid adding too many new navigation items until this flow works clearly.

### First implementation slice

The first farmer dashboard implementation should focus on:

1. a visible process tracker on the overview
2. a cow workflow board on `My herd`
3. clearer action-oriented alert cards
4. smaller, cleaner quick actions

## Problem Opportunity: Reproductive Knowledge And AI Access

Smallholder dairy farmers often operate with limited access to structured,
evidence-based reproductive guidance.

This creates a practical knowledge gap around:
- heat detection
- insemination timing
- conception follow-up
- pregnancy care
- dry-off timing
- feeding and preparation during gestation
- where to find affordable and reliable insemination support

The result is not just confusion.

It directly affects:
- calving interval length
- milk production
- reproductive efficiency
- veterinary follow-up
- household income

This means the dashboard should not only show animal records.

It should guide a farmer through the reproductive cycle in simple, usable steps.

## Research Signals Behind This Direction

The roadmap should reflect a few practical signals from dairy and smallholder
research:

- AI and other dairy technologies are useful, but uptake is strongly affected by
  provider access, cost, training, distance, and farmer linkages to service
  networks.
- Heat detection and insemination timing remain major failure points, so simple
  reminders and decision support are more valuable than heavy analytics.
- Timely pregnancy diagnosis matters because non-pregnant cows need to be
  identified early and returned to service quickly.
- Dry period planning still matters for productivity, so pregnancy management
  should not stop at insemination confirmation.
- Mobile-phone-based advisory has already been used in East African smallholder
  dairy settings, which supports building simple reminder and guidance flows
  instead of complex expert systems.

## Hackathon-Ready Reproductive Workflow

Keep the reproductive workflow short and easy to demo:

1. Farmer records the cow's last heat, calving date, or insemination date
2. System shows the next likely reproductive step
3. Farmer uses a simple heat-sign checker or opens the cow timeline
4. Farmer requests AI or veterinary follow-up
5. Vet or provider sees the request and logs the service outcome
6. System schedules pregnancy check follow-up
7. System later reminds the farmer about dry-off and calving preparation

This is a strong hackathon story because it connects:
- farmer education
- service access
- follow-up
- productivity

### Updated smooth workflow for the farmer and vet

The working product flow should now feel like one simple relationship with the
cow, not separate forms and pages.

1. Farmer clicks `Register Cow`
2. Farmer enters cow details:
   - cow number
   - cow name
   - breed
   - image
3. Farmer chooses the reproductive starting point:
   - `Not inseminated yet`
   - `Already inseminated`
   - `Pregnancy confirmed`
   - `Near calving`
4. If the cow is `Not inseminated yet`:
   - the farmer chooses the insemination type
   - the system creates a `Request insemination` record
   - the request later appears on the vet dashboard
   - the cow tracker shows `waiting for service`
5. If the cow is `Already inseminated`:
   - the farmer enters the insemination date
   - the system calculates the likely pregnancy timeline
   - the system predicts the possible calving date
6. After registration, the farmer is redirected immediately to the cow tracker
7. The tracker shows:
   - the cow stage
   - a calendar of important dates
   - pregnancy or calving progress
   - the next action to take
8. Later, the AI can use the same timeline and stored dates to explain:
   - what the farmer should expect
   - what changes to watch
   - when follow-up may be needed

### Registration design rule

The registration form should stay simple.

Do not show all reproductive fields at once.

Show the reproductive path first, then reveal only the relevant fields.

Example:

- If `Not inseminated yet`
  - show insemination request fields
  - show insemination type
  - do not show calving prediction yet

- If `Already inseminated`
  - show insemination date
  - show predicted follow-up and likely calving dates

- If `Pregnancy confirmed`
  - show confirmation date and expected calving date if known

- If `Near calving`
  - show expected calving date and calving watch actions

This makes the experience feel guided instead of heavy.

### Tracker design rule

The cow tracker should become the main working page after registration.

The tracker should show:
- cow photo and number
- current reproductive status
- day count since insemination when available
- predicted calving date
- visible calving window
- a small milestone timeline
- a calendar with highlighted important dates
- one clear next action

Important actions should be simple:
- `Request insemination`
- `Record insemination`
- `Confirm pregnancy`
- `Start calving watch`
- `Mark calved`
- `Needs attention`

### Vet dashboard support rule

The vet dashboard should not receive random case data only.

It should receive a clean insemination and follow-up workflow.

The minimum vet-side workflow should be:

1. new insemination requests appear in a queue
2. vet opens the request
3. vet records service outcome
4. system updates the cow tracker
5. system schedules pregnancy follow-up
6. alerts later surface near calving

This gives the project a clear farmer-to-vet-to-farmer loop.

### AI-ready data rule

Even before AI is integrated, the system should store the right reproductive
dates so AI can become useful later.

Useful data to store:
- reproductive status
- last observed heat
- insemination requested or not
- insemination type
- insemination date
- pregnancy check due date
- pregnancy confirmed or not
- predicted calving date
- actual calving date

This will later allow AI to explain:
- whether the cow may be returning to heat
- what signs are normal after insemination
- when pregnancy check should happen
- what to expect before calving

## Hackathon-Ready Milk Tracking Workflow

The milk workflow should stay simple and easy to use in the field.

It should not feel like a complicated dairy ERP.

### Main milk story

1. Farmer opens `Track Maziwa`
2. Farmer sees the list of registered cows
3. Farmer clicks one cow
4. Farmer records the milk amount for the day
5. The system stores the daily milk record
6. The cow detail page shows:
   - cow identity
   - recent milk entries
   - daily production trend
   - a simple productivity curve
7. The system later highlights:
   - stable production
   - rising production
   - falling production
   - unusual drop that may need review

### Track Maziwa page rule

The page should feel practical and farmer-friendly.

It should show:
- cow name
- cow number
- most recent milk amount
- quick action to record today
- quick action to open that cow

Do not overload it with too many dairy analytics in the first version.

### Cow milk detail page rule

When the farmer opens a specific cow from `Track Maziwa`, the page should show:
- cow name and image
- cow number
- breed
- current reproductive stage
- latest milk entries
- 7-day or 14-day milk summary
- a simple productivity curve
- one action to add a new milk record

The curve should be easy to read and should answer one question:

`Is this cow producing normally, improving, or dropping?`

### Milk productivity curve rule

For the hackathon, keep the chart simple:
- x-axis: days
- y-axis: liters of milk
- one line per cow on the cow detail page

Avoid advanced analytics at first.

The first chart only needs to help the farmer and judge see change clearly.

### Why Track Maziwa matters

This improves the product story because it connects reproductive tracking with
real farm output.

It helps answer questions like:
- is this cow producing less than expected?
- did milk change after insemination or calving?
- should the farmer watch the cow more closely?
- should the vet review a sudden drop?

This makes the product feel more practical and more valuable in a hackathon.

## Reproductive Features To Build First

### Farmer side

1. `Cow reproduction timeline`
- last calving date
- last observed heat
- insemination date
- pregnancy check due
- expected dry-off window

2. `Heat signs helper`
- simple yes or no symptom checklist
- show `watch`, `likely in heat`, or `seek service now`

3. `AI service access card`
- nearby or assigned service contact
- basic affordability note if pricing is available
- `Request insemination` or `Call provider`

4. `Pregnancy follow-up tracker`
- insemination recorded
- follow-up due date
- pregnancy confirmed or repeat service needed

5. `Dry-off and late-pregnancy checklist`
- when to stop milking
- feeding reminders
- calving preparation reminders

6. `Guided cow registration`
- register cow number, name, breed, and image
- choose reproductive starting point
- reveal only the relevant reproductive inputs

7. `Cow tracker page`
- open automatically after registration
- show timeline, progress, calendar, and next action

8. `Insemination request path`
- if not yet inseminated, create a request for service
- keep the cow visible as waiting for insemination

9. `Track Maziwa`
- list cows for milk recording
- record daily milk output per cow
- keep the page simple and fast to use

10. `Cow milk detail view`
- open one cow from `Track Maziwa`
- show recent milk records
- show a simple productivity curve
- link milk changes back to the cow context

### Vet or service-provider side

1. `AI requests queue`
- farmer name
- cow
- location
- urgency or due status

2. `Breeding follow-up board`
- inseminated cows
- pregnancy check due
- repeat service needed

3. `Pregnancy confirmation log`
- date checked
- result
- next recommendation

4. `Dry-off due list`
- cows approaching late gestation
- quick follow-up reminder

5. `Farmer guidance templates`
- short reusable guidance for heat signs
- pregnancy follow-up
- dry-off preparation

6. `Insemination request queue`
- requests from farmers who selected `not inseminated yet`
- service type visible
- request status visible

7. `Milk productivity watch list`
- cows with sudden milk drop
- cows needing follow-up
- quick visibility into farm-level productivity concerns

### Shared AI support

Keep AI support short and safe:

1. summarize what stage the farmer is likely in
2. highlight the next recommended action
3. suggest whether the case needs monitoring or provider follow-up

Do not use AI to make final clinical decisions automatically.

## Research Notes For The Roadmap

- Kenya technology-use research: stronger linkage to service providers helps
  technology uptake among smallholder dairy farmers.
  https://knowledge4policy.ec.europa.eu/publication/determinants-utilization-agricultural-technologies-among-smallholder-dairy-farmers_en
- Kenya AI adoption research: uptake of artificial insemination is influenced by
  farmer and access conditions, not only by awareness.
  https://erepository.uonbi.ac.ke/handle/11295/154460
- Dairy pregnancy detection guidance: timely pregnancy diagnosis helps identify
  non-pregnant cows so they can return to service sooner.
  https://dairy.extension.wisc.edu/dairy-worker-modules-reproductive-skills/
- Reproductive timing guidance: better heat detection and breeding timing reduce
  open days and long calving intervals.
  https://extension.psu.edu/animals-and-livestock/dairy/reproduction-and-genetics?cow_age_lactation_stage=Calves--Heifers
- Digital dairy advisory example: mobile-phone-based dairy guidance has already
  been used to promote AI, timely heat identification, and pregnancy management
  in East Africa.
  https://precisiondev.org/project/digital-agricultural-advisory-services-daas-advancing-livestock-productivity-for-ethiopian-smallholder-farmers/

## Farmer-Friendly Location Feature

For the location flow, farmers should not see technical map language.

### What the farmer should see

- `My farm location`
- `Use my current location`
- `Pin my farm on map`
- `Save location`
- `Location saved`

### What the system stores behind the scenes

- latitude
- longitude
- source
- updated time

This keeps the user experience simple while still giving the system the data it
needs.

## Simplified Location Flow

1. Farmer opens the location section
2. Farmer chooses one of:
   - `Use my current location`
   - `Pin my farm on map`
3. Farmer clicks `Save location`
4. System stores the location quietly in the background
5. Vet sees the farm on the map
6. Vet clicks `Get directions`

## Best Map Strategy For Hackathon

Start with the simplest version that works:

1. save a farm location
2. show the farm marker on the vet map
3. give the vet a `Get directions` button

Avoid building advanced real-time map features too early.

## Kenya-First Map Plan

The map should start focused on `Kenya`.

This keeps the experience simple and avoids unnecessary map complexity at the
beginning.

### Default map behavior

- map opens focused on Kenya
- users do not need to search the whole world
- the system stays relevant to the project context

### Area narrowing behavior

When a user enters or selects a location:
- the map should narrow down to that place
- the zoom should move closer automatically
- the selected area should become the current working focus

Examples:
- Kenya
- Meru
- a town
- a farm area

The farmer and the vet should both be able to guide the focus of the map when
needed, but only through simple actions.

## Automatic Farmer-To-Vet Location Flow

The vet should not need to search manually once the farmer has already saved the
farm location.

### Planned workflow

1. Farmer pins the farm location or uses current location
2. Farmer saves the location
3. The system stores the farm location
4. The saved location appears automatically on the vet map
5. The vet opens the map and immediately sees the destination

This should feel automatic and reduce unnecessary clicks.

## Planned Route Display Behavior

The route experience should stay simple and visually clear.

### Minimum version

- show the farm destination marker
- show the vet location if available
- allow the vet to open directions quickly

### Better visual version

- draw a visible route line on the map
- use a strong route color like red for urgent or active direction flow
- make the destination clear without cluttering the page

### Important note

There are two route display levels:

1. `Simple line`
- a straight visible line between the vet and the farm
- easiest version for early demos

2. `Route path`
- a route that follows actual roads
- better for realism
- should only be added after the simple version works

## Simple User-Facing Map Language

To keep the feature beginner-friendly, the interface should use simple labels.

### Farmer side

- `Set farm location`
- `Use my current location`
- `Pin my farm on map`
- `Save location`
- `Location saved`

### Vet side

- `Farm location`
- `Open map`
- `Get directions`
- `Destination`
- `Route to farm`

Do not expose technical language like:
- latitude
- longitude
- source
- raw map coordinates

## Recommended Hackathon Map Demo Flow

1. Farmer opens location section
2. Farmer pins the farm or uses current location
3. Farmer saves
4. Vet opens farm map
5. Farm appears automatically
6. Route or route line is shown
7. Vet follows the map decision flow

This is a strong demo because it is:
- clear
- visual
- useful
- easy to understand quickly

## Features To Build First

The first feature set should now support two connected stories:
- reproductive decision support
- location-aware service response when follow-up is needed

### Vet side

1. `Overview`
- urgent case visibility
- next visit visibility
- pregnancy check due visibility
- repeat service visibility
- quick links to active workflows

2. `Active Case`
- one active case at a time
- intervention log
- notes
- medications
- breeding outcome
- next action buttons

3. `Farm Map`
- farm markers
- simple status colors
- clear route handoff
- provider-to-farm response support

4. `My Farms`
- assigned farms
- alert counts
- due-soon counts
- cows needing reproductive follow-up

5. `Medical Records`
- recent history
- treatment summaries
- lab-linked notes
- pregnancy and breeding history

### Farmer side

1. `Cow reproduction timeline`
2. `Heat signs helper`
3. `Request insemination`
4. `Pregnancy follow-up tracker`
5. `Dry-off checklist`
6. `Set farm location`
7. `Use my current location`
8. `Pin my farm on map`
9. `Save location`

## Things To Avoid

To keep the project hackathon-ready, avoid:
- exposing technical fields to users
- overloading the homepage
- too many top-level nav items
- complex admin flows with low demo value
- real-time tracking before the basic version works
- advanced breeding analytics before the simple reproductive flow works
- advanced milk analytics before the daily logging workflow works
- hardware-dependent heat detection features for the first demo
- large provider marketplaces with too many filters
- long educational text where a checklist or next action would work better

## Build Order

1. keep the farmer dashboard simple and action-based
2. add guided cow registration with reproductive starting paths
3. redirect registration to the cow tracker page
4. add `Request insemination` for cows not yet inseminated
5. show insemination requests on the vet dashboard
6. add the cow reproduction timeline and calendar tracker
7. add pregnancy follow-up tracking and predicted calving dates
8. add `Track Maziwa` with daily milk entry per cow
9. add the cow milk detail page and productivity curve
10. surface simple milk-drop alerts
11. add the heat signs helper
12. add dry-off reminders and calving preparation checklist
13. add the farmer-friendly location flow
14. store farm coordinates in the backend
15. show farm markers on the vet map
16. add `Get directions`
17. improve only after the simple version works end-to-end

## Hackathon MVP Scope

To stay realistic for a hackathon, the strongest first demo should include only
the workflow that can be shown clearly from start to finish.

### Best MVP story

1. farmer registers a cow
2. farmer selects reproductive status
3. if not inseminated, the farmer requests insemination
4. the request appears on the vet dashboard
5. the vet records the service outcome
6. the system updates the cow tracker
7. the tracker shows progress and predicts the likely calving date
8. alerts appear later for follow-up and nearing calving

### Features that should be in the MVP

- guided cow registration
- insemination request creation
- vet request queue
- insemination recording
- pregnancy and calving tracker
- predicted calving timeline
- simple alerts

### Features that can form the next MVP extension

- `Track Maziwa`
- daily milk records per cow
- cow milk detail page
- simple productivity curve
- milk-drop follow-up alert

## Track Maziwa Build Roadmap

This feature should be built as a simple extension of the existing cow
workflow, not as a separate product.

### Goal

Help farmers record and understand daily milk output for each cow.

### Page structure

1. `Track Maziwa`
- list all cows
- show latest milk amount
- show quick entry action
- keep layout clean and fast

2. `Cow milk detail`
- cow information
- milk entry history
- productivity curve
- recent trend summary

### Data to store

The milk feature will need a simple daily record model later.

Minimum milk fields:
- cow
- date
- milk amount in liters
- optional session note
- created time

### Suggested first working flow

1. farmer opens `Track Maziwa`
2. farmer selects a cow
3. farmer records today's milk amount
4. system saves the entry
5. cow detail page updates the recent history
6. curve updates automatically
7. if milk drops sharply, the system can later raise a follow-up alert

### Hackathon-first design rules

- one cow at a time
- one daily number at a time
- one clear curve
- no heavy dashboard clutter
- no advanced dairy accounting in the first version

### Best implementation order for Track Maziwa

1. create a milk record model
2. add a `Track Maziwa` page to the farmer dashboard
3. add daily milk entry form
4. add a cow milk detail page
5. show a simple 7-day or 14-day productivity curve
6. add a basic drop-in-production alert
7. connect milk insights to later AI guidance

### Features that should wait until after the MVP works

- full farmer-vet chat
- complex route intelligence
- advanced breeding analytics
- AI conversation inside the tracker
- too many filters or provider roles

## Main Product Flow For Judges

The product should be easy to explain in a short demo.

### Demo flow

1. register a cow
2. choose `not inseminated yet` or `already inseminated`
3. create a service request or record insemination
4. open the tracker automatically
5. show the predicted progress and calving timeline
6. show the next action on the cow
7. show the same request or follow-up on the vet side

If this flow works cleanly, the project will feel useful, coherent, and
hackathon-ready.

## How To Make The Dashboards Hackathon-Winning

To stand out in a hackathon, the dashboards should not try to do everything.

They should feel:
- clear
- useful
- believable
- polished
- easy to demo in a few minutes

### 1. Solve one clear problem well

The dashboards should show one strong story:

- farmers can report important information simply
- vets can quickly understand what is urgent
- vets can decide what to do next
- vets can reach the farm faster

This is stronger than building many unrelated dashboard cards.

### 2. Keep each page focused on one main job

Each dashboard page should answer one question.

Examples:
- `Overview`: what needs attention right now?
- `Active Case`: what is happening in this case and what should I do next?
- `Farm Map`: where is the farm and how do I get there?
- `My Farms`: which farms need follow-up?
- `Medical Records`: what happened before?

This makes the product easier to understand for judges and users.

### 3. Make the user feel in control

The dashboard should never feel confusing or overloaded.

Good signs of control:
- one clear main action per page
- short labels
- few top-level navigation items
- important actions visible immediately
- extra detail hidden behind links instead of shown all at once

### 4. Show real usefulness, not just design

A good hackathon dashboard should help someone make a better decision.

Useful examples:
- urgent case highlighting
- clear case progress
- route guidance to the farm
- recent medical history before action
- simple AI support that suggests what to review next

Purely decorative sections should be avoided.

### 5. Keep the demo flow short and powerful

The best demo should be easy to follow.

Recommended demo story:

1. farmer saves farm location
2. system shows the farm on the map
3. vet opens the dashboard
4. vet sees the urgent case
5. vet opens the active case page
6. vet checks the map and gets directions

If the demo can be understood in under three minutes, the dashboard structure is
working well.

### 6. Use a simple but professional visual system

The dashboard should look intentional and consistent.

Use:
- one sidebar structure
- one typography direction
- one status color language
- repeated card styles
- clear spacing and hierarchy

Status colors should stay meaningful:
- red for urgent
- amber for monitoring
- green for clear
- blue for navigation, direction, or system support

### 7. Make the project structure look organized

A hackathon project feels stronger when the code structure is easy to explain.

Recommended separation:
- farmer workflows stay in farmer areas
- vet workflows stay in vet areas
- shared logic stays reusable
- dashboard pages stay task-based, not random

Important rule:
- do not mix public website content with dashboard workflow content

### 8. Build only features that can be demonstrated clearly

A feature should stay only if it improves the demo and works reliably.

Keep features that:
- help decision making
- help routing
- help communication
- help continuity of care

Avoid features that:
- are hard to explain
- are not connected to the main story
- look impressive but do not work end-to-end

### 9. Make the AI feel supportive, not risky

AI should support judgment, not replace the vet.

Good AI roles:
- summarize urgency
- suggest what to review next
- highlight possible risk
- provide a short recommendation

Bad AI roles:
- making final clinical decisions automatically
- replacing the vet's judgment
- giving long unclear paragraphs

### 10. Optimize for judging criteria

The dashboards should score well on common hackathon judging themes:

- `Impact`: solves a real farmer and veterinary coordination problem
- `Usability`: simple enough for beginners to understand
- `Technical quality`: clear working flow from user input to decision support
- `Design`: consistent, clean, and easy to navigate
- `Innovation`: useful AI plus map-assisted field response

## Project Structure Guidance

The project should stay easy to explain to judges and teammates.

### Recommended structure idea

- public website for landing and information
- farmer dashboard for simple reporting and farm-side actions
- vet dashboard for response, case review, and routing
- shared data models for farm, case, and location information
- shared AI support only where it improves action

### Dashboard architecture rule

Do not treat dashboards as a collection of random widgets.

Treat them as workflows.

That means:
- each dashboard page should have a job
- each job should connect to the next action
- each page should move the user forward

## Final Hackathon Standard

These dashboards should make a judge think:

`This team understood the real problem, built only what matters, and made it easy to use.`

## Success Standard

The product should feel like this:

### Farmer
`Set my location in one simple step`

### Vet
`See the farm, understand the case, and go there fast`
