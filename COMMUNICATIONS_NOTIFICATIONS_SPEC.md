# Communications, Notifications, and Cow Image Sharing Spec

## Purpose

This spec defines the hackathon-ready communication system that will let:

- farmers receive notifications about what needs attention
- veterinary users receive notifications about new work and replies
- farmers and veterinary users exchange messages in a shared thread
- users share cow images when a photo helps explain the case

This feature should support the main product story without turning the
dashboards into full chat products.

The goal is simple:

`Help a farmer raise a concern, share the right cow context, get a reply, and know the next action quickly.`

## Why This Feature Matters

The current roadmap already supports:

- cow registration
- insemination requests
- tracker updates
- farmer alerts
- provider discovery and first-contact messaging

What is still missing is the shared follow-up loop after first contact.

Without a communication layer:

- a farmer can send a message but cannot see a real reply thread
- the veterinary side cannot work from a proper inbox
- important updates stay fragmented across alerts, cards, and temporary page copy
- urgent visual context such as cow photos cannot be shared inside the workflow

This spec fills that gap.

## Current Confirmed Repo State

These facts are already true in the codebase:

- farmers can send a one-way provider message from the service finder
- a persisted `ServiceProviderMessage` model already exists in
  `farmers_dashboard`
- the `Cow` model already supports a `photo` field uploaded to `cow_photos/`
- farmer alerts already exist as cow-state-driven UI
- veterinary communication pages are still mostly presentation placeholders

This means the next implementation should extend the current flow instead of
building a separate second system.

## Product Scope

This feature has two connected surfaces:

1. `Notifications`
2. `Messages`

They should stay separate.

### Notifications

Notifications answer:

`What changed and what needs my attention now?`

Notifications are short, action-oriented, and usually link to another page.

### Messages

Messages answer:

`What was said, what image was shared, and what should I reply?`

Messages should live inside shared conversation threads.

## User Roles In Scope

Phase-one roles only:

- `farmer`
- `veterinary`

The design should remain role-scalable, but the first working flow should only
optimize for these two roles.

## Primary User Stories

### Farmer stories

- As a farmer, I want to send a message to a veterinary or AI service provider.
- As a farmer, I want to attach a cow image when text is not enough.
- As a farmer, I want to see whether the provider has replied.
- As a farmer, I want one place to review my conversation history.
- As a farmer, I want notifications when a provider replies or when my request status changes.

### Veterinary stories

- As a veterinary user, I want to see a queue of farmer conversations.
- As a veterinary user, I want to open a thread and reply clearly.
- As a veterinary user, I want to see which cow and farm the message is about.
- As a veterinary user, I want to review farmer-shared cow images before replying.
- As a veterinary user, I want notifications for new farmer messages and unread replies.

## Main Product Flow

### MVP message flow

1. Farmer opens `Service Finder`
2. Farmer selects a provider
3. Farmer writes a short message
4. Farmer optionally attaches an image of the cow
5. System creates a conversation thread and first message
6. System creates a notification for the veterinary user or mapped provider workspace
7. Veterinary user opens `Inbox`
8. Veterinary user reads the message, reviews the image, and replies
9. System creates a notification for the farmer
10. Farmer opens the reply from `Notifications` or `Messages`

### Later connected workflow

From a message thread, the user should be able to jump into:

- cow tracker
- insemination request
- active case
- farm map
- patient record

## UX Rules

### Rule 1: Separate triage from conversation

- Notifications should stay short and list-based.
- Messages should stay thread-based.
- Do not put full conversation threads on the dashboard homepages.

### Rule 2: One main job per page

- Notifications page: review new items and open the next action
- Messages page: read and reply clearly

### Rule 3: Keep image use purposeful

Images are for useful case context such as:

- visible discharge
- swelling
- body condition concern
- udder issue
- calving progress concern
- general cow identification when needed

Images should not turn the workflow into a social feed.

### Rule 4: Keep copy simple

Farmers should see clear labels such as:

- `Notifications`
- `Messages`
- `Attach cow image`
- `View thread`
- `Reply`
- `Mark as read`

Avoid technical media or messaging language.

## Recommended Architecture

## Shared App Decision

This feature should not live only inside `farmers_dashboard` because both roles
need the same communication records.

### Recommended option

Create a dedicated shared app:

- `communications`

This is the cleanest structure because it keeps:

- thread logic
- message logic
- notification logic
- attachment logic

out of role-specific dashboard apps.

### Acceptable faster option

If hackathon speed is the top priority, shared communication models may live in
`users`.

### Decision

Preferred implementation target:

- new app: `communications`

## Data Model Direction

### 1. `ConversationThread`

Purpose:

- represents one shared communication stream between a farmer and a veterinary user

Suggested fields:

- `farmer` -> FK to user
- `veterinary_user` -> FK to user, nullable during provider-directory transition
- `provider_key` -> char field for current directory compatibility
- `provider_name_snapshot`
- `provider_title_snapshot`
- `provider_service_type`
- `cow` -> FK to `farmers_dashboard.Cow`, nullable
- `insemination_request` -> FK to `farmers_dashboard.InseminationRequest`, nullable
- `subject` -> short text
- `status` -> `open`, `waiting_for_vet`, `waiting_for_farmer`, `closed`
- `last_message_at`
- `created_at`
- `updated_at`

Important note:

The current service finder uses provider directory snapshots rather than real
provider accounts for every entry. The thread must support that transition.

### 2. `ConversationMessage`

Purpose:

- stores each actual message sent in the thread

Suggested fields:

- `thread` -> FK
- `sender` -> FK to user
- `sender_role_snapshot`
- `body`
- `is_read`
- `read_at`
- `created_at`

### 3. `MessageImageAttachment`

Purpose:

- stores optional images shared inside a message

Suggested fields:

- `message` -> FK
- `image`
- `caption` blank
- `created_at`

Suggested upload location:

- `message_attachments/%Y/%m/`

Validation rules:

- allow `jpg`, `jpeg`, `png`, `webp`
- block unsupported file types
- enforce size limit
- keep count per message small

### 4. `Notification`

Purpose:

- stores action-oriented alerts for one recipient

Suggested fields:

- `recipient` -> FK to user
- `actor` -> FK to user, nullable
- `notification_type`
- `title`
- `body`
- `action_url`
- `thread` nullable
- `cow` nullable
- `insemination_request` nullable
- `is_read`
- `read_at`
- `created_at`

## Attachment Strategy

Users should be able to share cow images in two ways:

### Option A: Attach an existing cow photo reference

If the cow already has a profile image on the `Cow` record:

- the message composer can show `Use current cow photo`
- the thread can display that image as linked case context

### Option B: Upload a fresh case image

If the farmer needs to show a new issue:

- the message composer should allow image upload
- the upload should attach to the specific message, not overwrite the cow profile photo

### Decision

Support both options.

Why:

- the existing cow photo helps with identity
- a fresh uploaded image helps with current symptoms or calving status

## First Notification Types

### Farmer notification types

- `provider_replied`
- `insemination_request_accepted`
- `insemination_request_completed`
- `pregnancy_check_due`
- `calving_watch_due`
- `cow_needs_attention`

### Veterinary notification types

- `new_farmer_message`
- `new_insemination_request`
- `farmer_replied`
- `follow_up_due`
- `near_calving_alert`

Only build the first message-related notification types in the initial slice.

## Access Control Rules

### Farmer access

A farmer can:

- view only their own threads
- send messages only from their own account
- attach images only to their own outgoing messages
- view only notifications addressed to them

### Veterinary access

A veterinary user can:

- view only threads assigned to them or their current provider mapping
- reply only within accessible threads
- view only notifications addressed to them

### Safety rule

Do not allow one farmer to view another farmer's thread, message, images, or notifications.

## Page Specifications

### Farmer `Notifications` page

Route:

- `/farmers/notifications/`

Main question:

`What changed and what should I open next?`

Page sections:

- summary row: unread, urgent, today
- notification list
- clear action button per item

Typical item content:

- title
- short explanation
- linked cow if present
- time
- `Open thread` or `Open cow`

### Farmer `Messages` page

Route:

- `/farmers/messages/`

Main question:

`Who have I contacted, what did they say, and what should I reply?`

Layout:

- left: thread list
- right: selected thread
- bottom: reply box with optional image upload

Thread list should show:

- provider name
- latest message preview
- unread state
- related cow if present
- last updated time

Thread detail should show:

- sender
- message text
- attached images
- related cow context
- reply composer

### Veterinary `Notifications` page

Route:

- `/veterinary/notifications/`

Main question:

`Which new messages or follow-ups need attention first?`

Layout:

- triage summary
- unread-first list
- quick link into inbox, patient, or schedule

### Veterinary `Inbox` page

Route:

- `/veterinary/messages/`

Main question:

`Which farmer needs a reply, and what cow context do I have?`

Layout:

- left: conversation list
- right: selected thread
- side context area or top summary for cow/farm details
- reply composer with optional image upload

## Sidebar And Badge Rules

Both dashboards should show:

- `Notifications`
- `Messages`

Badges:

- unread notification count
- unread message-thread count

Important rule:

Only show compact badges.
Do not turn the sidebar into a dashboard inside the dashboard.

## Image Handling Rules

### Allowed image sources

- existing cow profile image
- newly uploaded message attachment

### Allowed formats

- `.jpg`
- `.jpeg`
- `.png`
- `.webp`

### Suggested limits for MVP

- max 3 images per message
- max 5 MB per image

### Display rules

- show image thumbnails in the thread
- open full image in a simple preview or direct file link
- keep layouts stable even when no image is attached

### Privacy rule

Only users with thread access can open the image.

## Status And Read-State Rules

### Thread status behavior

- after farmer sends first message: `waiting_for_vet`
- after veterinary user replies: `waiting_for_farmer`
- after farmer replies again: `waiting_for_vet`
- closed threads remain readable but not actively highlighted

### Read-state behavior

- opening a thread marks visible unread incoming messages as read
- opening the notifications page does not automatically mark everything as read
- use explicit per-item read behavior or mark-on-open action

## Backward Compatibility Plan

The repo already contains `ServiceProviderMessage`.

Implementation should avoid breaking existing data.

### Safe migration path

1. introduce new shared communication models
2. keep `ServiceProviderMessage` temporarily
3. update new message creation to write to the new thread/message models
4. optionally backfill old `ServiceProviderMessage` records into threads later
5. remove or deprecate old model only after the new workflow is stable

This matches the repository rule to prefer additive schema changes first.

## Suggested URL Plan

### Farmer

- `/farmers/notifications/`
- `/farmers/messages/`
- `/farmers/messages/<thread_id>/`

### Veterinary

- `/veterinary/notifications/`
- `/veterinary/messages/`
- `/veterinary/messages/<thread_id>/`

### Shared actions

Use POST actions for:

- send message
- reply
- mark notification read
- mark thread closed

## Service Layer Direction

Create shared services to keep views small.

Suggested service helpers:

- `create_thread_from_service_finder(...)`
- `send_thread_message(...)`
- `create_notification(...)`
- `mark_thread_messages_read(...)`
- `get_threads_for_user(...)`
- `get_notifications_for_user(...)`

This keeps business logic out of templates and reduces role-specific duplication.

## Forms Direction

Suggested forms:

- `ConversationStartForm`
- `ConversationReplyForm`
- `NotificationReadForm`

Reply form should support:

- message body
- optional image attachments
- optional `use current cow photo` checkbox when a cow is linked

## Testing Requirements

Minimum tests for the first implementation:

- farmer can create a thread from service finder
- veterinary user can view assigned thread
- veterinary user can reply
- farmer sees a reply notification
- unauthorized users cannot access another user thread
- image upload validation rejects unsupported types
- read state changes correctly when thread is opened

## Build Order

### Phase 1: Shared communication foundation

1. create `communications` app
2. add `ConversationThread`
3. add `ConversationMessage`
4. add `MessageImageAttachment`
5. add `Notification`
6. generate and review migrations

### Phase 2: Farmer messaging flow

1. update service finder send flow
2. create farmer messages page
3. create farmer reply form
4. show image attachments in thread

### Phase 3: Veterinary inbox flow

1. create veterinary inbox page
2. wire real thread query into inbox
3. add reply action
4. show cow context and image attachments

### Phase 4: Notifications

1. create shared notification helpers
2. create farmer notifications page
3. create veterinary notifications page
4. add unread badges to both sidebars

### Phase 5: Workflow connection

1. link thread to cow tracker
2. link thread to insemination request when relevant
3. surface message-related callouts from key workflow pages

## MVP Cut Line

The first demo-ready slice should include only:

- farmer can send a message from service finder
- farmer can attach a cow image
- veterinary user can see the message in inbox
- veterinary user can reply
- farmer receives a notification for the reply
- both can reopen the same thread later

Do not add these before the above works end-to-end:

- group chat
- live websocket updates
- typing indicators
- audio messages
- video calls
- advanced media galleries
- large provider marketplace features

## Open Implementation Decisions

These should be resolved before coding starts:

1. How provider-directory records map to real veterinary users in the first release
2. Whether old `ServiceProviderMessage` data needs backfill immediately or later
3. Whether veterinary users may also upload reply images in the MVP
4. Whether message attachments should allow more than one image in the first slice

## Recommended Decisions

To keep implementation safe and fast:

1. Map only provider entries that correspond to real veterinary workspace users in MVP
2. Defer backfill of old `ServiceProviderMessage` records unless needed for demo continuity
3. Allow veterinary reply images in MVP only if the form complexity stays manageable
4. Start with one image per message if implementation time is tight, even though the model can support more later

## Success Standard

This feature is successful when:

- a farmer can raise a concern in one clear step
- a useful cow image can be shared when needed
- the veterinary user can reply from one inbox
- both roles receive clear notifications
- the workflow feels focused, not chat-heavy
- the feature strengthens the reproductive and calving support story

## Implementation Rule

When this spec is implemented:

- follow `TEAM_RULES.md`
- follow `ENGINEERING_INSTRUCTIONS.md`
- follow `DATABASE_CHANGE_RULES.md`
- use additive schema changes first
- verify migrations, Django checks, and targeted tests before completion
