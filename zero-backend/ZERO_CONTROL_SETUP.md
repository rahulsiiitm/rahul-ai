# ZERO Control Room — Phase 1 setup

This phase adds persistent chatbot telemetry without changing the public chat experience.

## 1. Create a Supabase project

Use a dedicated Supabase project or an existing project you control.

## 2. Run the database migration

Open the Supabase SQL editor and run:

`supabase/001_zero_control.sql`

This creates:

- `zero_sessions`
- `zero_messages`
- `zero_events`
- `zero_leads`
- `touch_zero_session(...)` backend RPC

All four tables have Row Level Security enabled. Anonymous access is revoked. Authenticated dashboard reads are only allowed when the authenticated user's `app_metadata.role` is `zero_admin`.

## 3. Add backend environment variables

Add these only to the ZERO backend deployment:

```env
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_SERVICE_ROLE_KEY=YOUR_SERVICE_ROLE_KEY
TELEMETRY_HASH_SALT=generate-a-long-random-secret
```

Never expose `SUPABASE_SERVICE_ROLE_KEY` through a `NEXT_PUBLIC_...` variable or browser bundle.

`TELEMETRY_HASH_SALT` is used to HMAC client IP addresses into stable visitor hashes. Raw IP addresses are not stored.

If any of the Supabase variables are missing or Supabase is unavailable, telemetry silently degrades and ZERO continues serving chat normally.

## 4. What gets logged

### Sessions

- generated chat session ID
- privacy-preserving visitor hash
- user agent
- referrer
- created / last active timestamps
- message count

### Messages

- session ID
- user / assistant role
- content
- selected provider and model for assistant messages
- total response latency
- response status

### Events

Examples:

- `provider_attempt`
- `provider_failure`
- `provider_selected`
- `stream_interrupted`
- `response_complete`
- `rate_limited`
- `history_cleared`
- `all_providers_unavailable`

Provider failures record only the exception class, not raw exception text, credentials, headers, or secrets.

## 5. Admin user setup

The private dashboard will use Supabase Auth in Phase 2.

The account allowed to view Control Room data must receive:

```json
{
  "role": "zero_admin"
}
```

inside its Supabase Auth `app_metadata`.

Do not put authorization roles in user-editable metadata.

## Phase 2

The next PR will add the private portfolio route, authentication gate, and dashboard views for sessions, conversations, provider health, latency, failures, and leads.
