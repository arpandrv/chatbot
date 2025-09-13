BEGIN;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ---------- Types ----------
CREATE TYPE chat_role AS ENUM ('user','bot','system');
CREATE TYPE fsm_state AS ENUM ('welcome','support_people','strengths','worries','goals','llm_conversation');

-- ---------- sessions (now REQUIRED to be linked to a Supabase user) ----------
CREATE TABLE IF NOT EXISTS public.sessions (
  session_id      uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id         uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  fsm_state       fsm_state NOT NULL DEFAULT 'welcome',
  status          text NOT NULL DEFAULT 'active' CHECK (status IN ('active','ended','expired')),
  created_at      timestamptz NOT NULL DEFAULT now(),
  last_activity   timestamptz NOT NULL DEFAULT now(),
  ended_at        timestamptz
);

CREATE INDEX IF NOT EXISTS sessions_user_idx
  ON public.sessions (user_id, last_activity DESC);

CREATE INDEX IF NOT EXISTS sessions_last_activity_idx
  ON public.sessions (last_activity DESC);

-- ---------- chat_history (single source of truth) ----------
CREATE TABLE IF NOT EXISTS public.chat_history (
  id                bigserial PRIMARY KEY,
  session_id        uuid NOT NULL REFERENCES public.sessions(session_id) ON DELETE CASCADE,
  role              chat_role NOT NULL,
  message           text,
  message_type      text NOT NULL DEFAULT 'text',          -- 'text' | 'fsm_response' | 'crisis_resources' | ...
  meta              jsonb NOT NULL DEFAULT '{}'::jsonb,
  ts                timestamptz NOT NULL DEFAULT now(),

  -- folded "user_responses":
  fsm_step          fsm_state NULL,                        -- NULL for ordinary turns
  is_final_response boolean NOT NULL DEFAULT FALSE         -- exactly one TRUE per (session, step)
);

CREATE INDEX IF NOT EXISTS chat_history_session_ts_idx
  ON public.chat_history (session_id, ts);

CREATE INDEX IF NOT EXISTS chat_history_role_idx
  ON public.chat_history (role);

CREATE INDEX IF NOT EXISTS chat_history_session_step_ts_idx
  ON public.chat_history (session_id, fsm_step, ts DESC);

-- One accepted response per (session, step)
CREATE UNIQUE INDEX IF NOT EXISTS chat_history_unique_final_per_step
  ON public.chat_history (session_id, fsm_step)
  WHERE is_final_response IS TRUE;

-- Your rule: LLM phase rows must be final
ALTER TABLE public.chat_history
  DROP CONSTRAINT IF EXISTS chat_history_llm_final_ck,
  ADD  CONSTRAINT chat_history_llm_final_ck
       CHECK (fsm_step IS DISTINCT FROM 'llm_conversation' OR is_final_response = TRUE);

-- Keep sessions hot on new messages
CREATE OR REPLACE FUNCTION public.bump_last_activity() RETURNS trigger AS $$
BEGIN
  UPDATE public.sessions SET last_activity = now() WHERE session_id = NEW.session_id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_chat_bump_activity ON public.chat_history;
CREATE TRIGGER trg_chat_bump_activity
AFTER INSERT ON public.chat_history
FOR EACH ROW EXECUTE FUNCTION public.bump_last_activity();

-- Auto-finalize user turns during llm_conversation
CREATE OR REPLACE FUNCTION public.ch_auto_final_llm() RETURNS trigger AS $$
BEGIN
  IF NEW.fsm_step = 'llm_conversation' AND NEW.role = 'user' THEN
    NEW.is_final_response := TRUE;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_ch_auto_final_llm ON public.chat_history;
CREATE TRIGGER trg_ch_auto_final_llm
BEFORE INSERT ON public.chat_history
FOR EACH ROW EXECUTE FUNCTION public.ch_auto_final_llm();

-- ---------- risk_detections ----------
CREATE TABLE IF NOT EXISTS public.risk_detections (
  id              bigserial PRIMARY KEY,
  session_id      uuid NOT NULL REFERENCES public.sessions(session_id) ON DELETE CASCADE,
  message_id      bigint REFERENCES public.chat_history(id) ON DELETE SET NULL,
  label           text NOT NULL,              -- 'risk' | 'no_risk'
  confidence      double precision,
  method          text,                       -- 'huggingface_fallback' | 'llm' | ...
  model           text,
  details         jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS risk_detections_session_idx
  ON public.risk_detections (session_id, created_at DESC);

-- ---------- intent_classifications ----------
CREATE TABLE IF NOT EXISTS public.intent_classifications (
  id              bigserial PRIMARY KEY,
  session_id      uuid NOT NULL REFERENCES public.sessions(session_id) ON DELETE CASCADE,
  message_id      bigint REFERENCES public.chat_history(id) ON DELETE SET NULL,
  label           text NOT NULL,
  confidence      double precision,
  method          text,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS intent_cls_session_idx
  ON public.intent_classifications (session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS intent_cls_message_idx
  ON public.intent_classifications (message_id);


-- ---------- RLS (enabled; backend service_role bypasses) ----------
ALTER TABLE public.sessions               ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_history           ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.risk_detections        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.intent_classifications ENABLE ROW LEVEL SECURITY;


COMMIT;




-----optional additions and information below-----

-- ---------- optional system_logs (only if you wire a DB log handler) ----------
-- CREATE TABLE IF NOT EXISTS public.system_logs (
--   id              bigserial PRIMARY KEY,
--   level           text NOT NULL,              -- info | warning | error
--   message         text NOT NULL,
--   context         jsonb NOT NULL DEFAULT '{}'::jsonb,
--   created_at      timestamptz NOT NULL DEFAULT now()
-- );

-- CREATE INDEX IF NOT EXISTS system_logs_level_idx
--   ON public.system_logs (level, created_at DESC);

-- ALTER TABLE public.system_logs            ENABLE ROW LEVEL SECURITY;

-- Optional client-side policies for later (commented):
-- CREATE POLICY "own sessions" ON public.sessions
--   FOR SELECT USING (user_id = auth.uid());
-- CREATE POLICY "own chat" ON public.chat_history
--   FOR SELECT USING (session_id IN (SELECT session_id FROM public.sessions WHERE user_id = auth.uid()));
