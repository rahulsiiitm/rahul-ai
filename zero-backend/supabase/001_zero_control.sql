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

-- One backend-only RPC keeps session counters and activity timestamps accurate.
create or replace function public.touch_zero_session(
    p_session_id text,
    p_visitor_hash text default null,
    p_user_agent text default null,
    p_referrer text default null
)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
    insert into public.zero_sessions (
        session_id,
        visitor_hash,
        user_agent,
        referrer,
        message_count
    )
    values (
        p_session_id,
        p_visitor_hash,
        p_user_agent,
        p_referrer,
        1
    )
    on conflict (session_id) do update
    set
        last_active_at = now(),
        message_count = public.zero_sessions.message_count + 1,
        visitor_hash = coalesce(public.zero_sessions.visitor_hash, excluded.visitor_hash),
        user_agent = coalesce(excluded.user_agent, public.zero_sessions.user_agent),
        referrer = coalesce(excluded.referrer, public.zero_sessions.referrer);
end;
$$;

revoke all on function public.touch_zero_session(text, text, text, text) from public, anon, authenticated;
grant execute on function public.touch_zero_session(text, text, text, text) to service_role;

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
-- Supabase recommends app metadata, rather than user-editable metadata, for authorization data.
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
