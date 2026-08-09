-- ZERO Control Room: persistent observability schema

create table if not exists public.zero_sessions (
    id uuid primary key default gen_random_uuid(),
    session_id text not null unique,
    visitor_hash text,
    user_agent text,
    referrer text,
    created_at timestamptz not null default now(),
    last_active_at timestamptz not null default now(),
    message_count integer not null default 0
);

create table if not exists public.zero_messages (
    id uuid primary key default gen_random_uuid(),
    session_id text not null,
    role text not null check (role in ('user', 'assistant', 'system')),
    content text not null,
    provider text,
    model text,
    latency_ms integer,
    status text not null default 'ok',
    created_at timestamptz not null default now()
);

create table if not exists public.zero_events (
    id uuid primary key default gen_random_uuid(),
    session_id text,
    event_type text not null,
    provider text,
    model text,
    latency_ms integer,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists public.zero_leads (
    id uuid primary key default gen_random_uuid(),
    session_id text,
    email text not null,
    message text not null,
    status text not null default 'new',
    created_at timestamptz not null default now()
);

create index if not exists zero_sessions_last_active_idx on public.zero_sessions (last_active_at desc);
create index if not exists zero_messages_session_idx on public.zero_messages (session_id, created_at);
create index if not exists zero_messages_created_idx on public.zero_messages (created_at desc);
create index if not exists zero_events_session_idx on public.zero_events (session_id, created_at);
create index if not exists zero_events_type_idx on public.zero_events (event_type, created_at desc);
create index if not exists zero_leads_created_idx on public.zero_leads (created_at desc);

alter table public.zero_sessions enable row level security;
alter table public.zero_messages enable row level security;
alter table public.zero_events enable row level security;
alter table public.zero_leads enable row level security;

revoke all on public.zero_sessions from anon;
revoke all on public.zero_messages from anon;
revoke all on public.zero_events from anon;
revoke all on public.zero_leads from anon;

grant select on public.zero_sessions to authenticated;
grant select on public.zero_messages to authenticated;
grant select on public.zero_events to authenticated;
grant select on public.zero_leads to authenticated;

-- The dashboard user will receive app_metadata.role = 'zero_admin'.
-- raw app metadata is appropriate for authorization because end users cannot edit it themselves.
create policy "zero_admin_read_sessions"
    on public.zero_sessions for select
    to authenticated
    using ((select auth.jwt()->'app_metadata'->>'role') = 'zero_admin');

create policy "zero_admin_read_messages"
    on public.zero_messages for select
    to authenticated
    using ((select auth.jwt()->'app_metadata'->>'role') = 'zero_admin');

create policy "zero_admin_read_events"
    on public.zero_events for select
    to authenticated
    using ((select auth.jwt()->'app_metadata'->>'role') = 'zero_admin');

create policy "zero_admin_read_leads"
    on public.zero_leads for select
    to authenticated
    using ((select auth.jwt()->'app_metadata'->>'role') = 'zero_admin');
