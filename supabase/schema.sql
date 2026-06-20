-- ============================================================
-- JOB SEARCH SYSTEM — MULTI-TENANT SUPABASE SCHEMA
-- Run this in Supabase SQL Editor (Project → SQL Editor → New query)
--
-- This script is IDEMPOTENT: it is safe to run repeatedly. Every policy,
-- trigger and index is dropped-if-exists before being (re)created, and all
-- tables use CREATE TABLE IF NOT EXISTS, so re-running NEVER drops your data
-- and never errors with "policy/trigger already exists".
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- TABLE: user_profiles
-- Per-user search configuration (roles, salary, locations, etc.)
-- ============================================================
CREATE TABLE IF NOT EXISTS user_profiles (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
    full_name       TEXT,
    email           TEXT,
    target_roles    TEXT[]  DEFAULT '{}',          -- e.g. {"research manager","team lead research"}
    salary_floor    INTEGER DEFAULT 0,             -- in INR lakhs per annum
    locations       TEXT[]  DEFAULT '{}',          -- e.g. {"Hyderabad","Bangalore","Remote"}
    experience_years INTEGER DEFAULT 0,
    industries      TEXT[]  DEFAULT '{}',          -- e.g. {"BFSI","Consulting","KPO"}
    target_companies TEXT[] DEFAULT '{}',          -- override list, empty = scrape all
    exclude_companies TEXT[] DEFAULT '{}',
    is_active       BOOLEAN DEFAULT TRUE,
    gmail_connected BOOLEAN DEFAULT FALSE,
    -- Optional Naukri auto-refresh credentials (used by naukri_refresh.py).
    -- Opt-in only; many users leave these null.
    naukri_email    TEXT,
    naukri_password TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Backfill the optional Naukri columns on pre-existing installs.
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS naukri_email    TEXT;
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS naukri_password TEXT;
-- Master resume text — powers resume-aware job matching (M4).
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS resume_text     TEXT;
-- Last manual "Refresh Now" time — used to rate-limit non-admin refreshes.
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS last_manual_refresh TIMESTAMPTZ;

ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own profile"   ON user_profiles;
DROP POLICY IF EXISTS "Users can insert own profile" ON user_profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON user_profiles;

CREATE POLICY "Users can view own profile"
    ON user_profiles FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own profile"
    ON user_profiles FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own profile"
    ON user_profiles FOR UPDATE USING (auth.uid() = user_id);

-- ============================================================
-- TABLE: gmail_tokens
-- OAuth tokens per user. Scrapers read these at runtime (service role).
-- ============================================================
CREATE TABLE IF NOT EXISTS gmail_tokens (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
    access_token    TEXT NOT NULL,
    refresh_token   TEXT NOT NULL,
    token_expiry    TIMESTAMPTZ,
    scope           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE gmail_tokens ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role only"               ON gmail_tokens;
DROP POLICY IF EXISTS "Users can view own token status" ON gmail_tokens;
DROP POLICY IF EXISTS "Users can upsert own tokens"     ON gmail_tokens;
DROP POLICY IF EXISTS "Users can update own tokens"     ON gmail_tokens;

-- Only service role can read tokens (scrapers use service key)
CREATE POLICY "Service role only"
    ON gmail_tokens FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Users can view own token status"
    ON gmail_tokens FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can upsert own tokens"
    ON gmail_tokens FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own tokens"
    ON gmail_tokens FOR UPDATE USING (auth.uid() = user_id);

-- ============================================================
-- TABLE: job_feed
-- All scraped jobs, tagged per user.
-- ============================================================
CREATE TABLE IF NOT EXISTS job_feed (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Core job data
    job_title       TEXT NOT NULL,
    company         TEXT NOT NULL,
    location        TEXT,
    salary_range    TEXT,
    job_url         TEXT NOT NULL,
    description_snippet TEXT,
    posted_date     DATE,
    source          TEXT NOT NULL,   -- "workday","greenhouse","lever","gmail_naukri","iimjobs", etc.
    source_job_id   TEXT,            -- ID from the source system for dedup

    -- Classification
    job_type        TEXT DEFAULT 'full_time',  -- full_time, contract, internship
    experience_required TEXT,
    seniority       TEXT,            -- junior, mid, senior, lead, manager, director

    -- Status
    is_new          BOOLEAN DEFAULT TRUE,
    is_applied      BOOLEAN DEFAULT FALSE,
    is_saved        BOOLEAN DEFAULT FALSE,
    is_dismissed    BOOLEAN DEFAULT FALSE,

    -- Match scoring (computed by filter.py)
    match_score     FLOAT DEFAULT 0,
    match_reasons   JSONB DEFAULT '[]',

    scraped_at      TIMESTAMPTZ DEFAULT NOW(),
    created_at      TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id, source, source_job_id)
);

CREATE INDEX IF NOT EXISTS idx_job_feed_user_id     ON job_feed(user_id);
CREATE INDEX IF NOT EXISTS idx_job_feed_scraped_at  ON job_feed(scraped_at DESC);
CREATE INDEX IF NOT EXISTS idx_job_feed_source      ON job_feed(source);
CREATE INDEX IF NOT EXISTS idx_job_feed_is_new      ON job_feed(is_new) WHERE is_new = TRUE;

ALTER TABLE job_feed ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own jobs"      ON job_feed;
DROP POLICY IF EXISTS "Service role can insert jobs" ON job_feed;
DROP POLICY IF EXISTS "Users can insert own jobs"    ON job_feed;
DROP POLICY IF EXISTS "Users can update own jobs"    ON job_feed;
DROP POLICY IF EXISTS "Users can delete own jobs"    ON job_feed;

CREATE POLICY "Users can view own jobs"
    ON job_feed FOR SELECT USING (auth.uid() = user_id);
-- The scraper uses the service-role key (bypasses RLS), so this INSERT policy
-- only governs the anon/authenticated client. It must NOT be WITH CHECK (TRUE) —
-- that let any signed-in user insert rows into ANOTHER user's feed. Restrict to
-- the user's own rows; the service role is unaffected.
CREATE POLICY "Users can insert own jobs"
    ON job_feed FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own jobs"
    ON job_feed FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own jobs"
    ON job_feed FOR DELETE USING (auth.uid() = user_id);

-- ============================================================
-- TABLE: applications
-- 18-stage application tracking
-- ============================================================
CREATE TABLE IF NOT EXISTS applications (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    job_feed_id     UUID REFERENCES job_feed(id) ON DELETE SET NULL,

    -- Core info
    company         TEXT NOT NULL,
    job_title       TEXT NOT NULL,
    job_url         TEXT,
    location        TEXT,
    salary_offered  TEXT,
    job_type        TEXT DEFAULT 'full_time',

    -- 18-stage tracking
    stage           TEXT NOT NULL DEFAULT 'Not Applied' CHECK (stage IN (
        'Not Applied',
        'Applied',
        'Application Acknowledged',
        'Recruiter Screening',
        'HM Interview Scheduled',
        'HM Interview Done',
        'Technical Round Scheduled',
        'Technical Round Done',
        'Case Study / Assignment',
        'Final Round Scheduled',
        'Final Round Done',
        'Reference Check',
        'Background Check',
        'Offer Verbal',
        'Offer Written',
        'Offer Negotiating',
        'Offer Accepted',
        'Rejected',
        'Withdrawn',
        'Ghosted'
    )),

    -- Dates
    date_applied        DATE,
    date_stage_updated  DATE DEFAULT CURRENT_DATE,
    follow_up_date      DATE,
    next_action         TEXT,

    -- Contacts
    recruiter_name      TEXT,
    recruiter_email     TEXT,
    recruiter_linkedin  TEXT,
    hiring_manager_name TEXT,
    referral_contact    TEXT,

    -- Notes
    notes               TEXT,
    prep_notes          TEXT,
    rejection_reason    TEXT,

    -- Source
    source              TEXT,   -- where job was found
    priority            TEXT DEFAULT 'medium' CHECK (priority IN ('high', 'medium', 'low')),

    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_applications_user_id   ON applications(user_id);
CREATE INDEX IF NOT EXISTS idx_applications_stage     ON applications(stage);
CREATE INDEX IF NOT EXISTS idx_applications_follow_up ON applications(follow_up_date) WHERE follow_up_date IS NOT NULL;

ALTER TABLE applications ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can manage own applications" ON applications;
CREATE POLICY "Users can manage own applications"
    ON applications FOR ALL USING (auth.uid() = user_id);

-- ============================================================
-- TABLE: referral_pipeline
-- ============================================================
CREATE TABLE IF NOT EXISTS referral_pipeline (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    company         TEXT NOT NULL,
    contact_name    TEXT NOT NULL,
    contact_role    TEXT,
    contact_linkedin TEXT,
    contact_email   TEXT,

    status          TEXT DEFAULT 'identified' CHECK (status IN (
        'identified',
        'message_drafted',
        'message_sent',
        'responded',
        'call_scheduled',
        'referred',
        'not_responding',
        'declined'
    )),

    message_sent_date   DATE,
    response_date       DATE,
    follow_up_date      DATE,
    notes               TEXT,

    application_id  UUID REFERENCES applications(id) ON DELETE SET NULL,

    connection_type TEXT CHECK (connection_type IN (
        'linkedin_1st', 'linkedin_2nd', 'linkedin_3rd',
        'alumni', 'ex_colleague', 'cold'
    )),

    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_referral_pipeline_user_id ON referral_pipeline(user_id);

ALTER TABLE referral_pipeline ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can manage own referral pipeline" ON referral_pipeline;
CREATE POLICY "Users can manage own referral pipeline"
    ON referral_pipeline FOR ALL USING (auth.uid() = user_id);

-- ============================================================
-- TABLE: message_templates
-- ============================================================
CREATE TABLE IF NOT EXISTS message_templates (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    name            TEXT NOT NULL,       -- e.g. "LinkedIn Referral - Finance Role"
    template_type   TEXT NOT NULL CHECK (template_type IN (
        'linkedin_referral', 'email_referral',
        'follow_up', 'thank_you', 'withdrawal', 'custom'
    )),
    subject_line    TEXT,
    body            TEXT NOT NULL,
    variables       TEXT[] DEFAULT '{}',

    is_default      BOOLEAN DEFAULT FALSE,
    use_count       INTEGER DEFAULT 0,

    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE message_templates ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can manage own templates" ON message_templates;
CREATE POLICY "Users can manage own templates"
    ON message_templates FOR ALL USING (auth.uid() = user_id);

-- ============================================================
-- TABLE: contacts
-- ============================================================
CREATE TABLE IF NOT EXISTS contacts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    name            TEXT NOT NULL,
    company         TEXT,
    role            TEXT,
    email           TEXT,
    linkedin_url    TEXT,
    phone           TEXT,

    relationship    TEXT,
    notes           TEXT,
    tags            TEXT[] DEFAULT '{}',

    last_contacted  DATE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can manage own contacts" ON contacts;
CREATE POLICY "Users can manage own contacts"
    ON contacts FOR ALL USING (auth.uid() = user_id);

-- ============================================================
-- TABLE: scraper_health
-- ============================================================
CREATE TABLE IF NOT EXISTS scraper_health (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source          TEXT NOT NULL,
    last_run_at     TIMESTAMPTZ,
    last_success_at TIMESTAMPTZ,
    last_job_count  INTEGER DEFAULT 0,
    consecutive_failures INTEGER DEFAULT 0,
    last_error      TEXT,
    status          TEXT DEFAULT 'ok' CHECK (status IN ('ok', 'warning', 'error')),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(source)
);

ALTER TABLE scraper_health ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role manages health" ON scraper_health;
DROP POLICY IF EXISTS "Users can read health"       ON scraper_health;
CREATE POLICY "Service role manages health"
    ON scraper_health FOR ALL USING (auth.role() = 'service_role');
-- Authenticated users only — last_error can contain stack traces / internal
-- URLs, so it must not be world-readable via the anon key.
CREATE POLICY "Users can read health"
    ON scraper_health FOR SELECT USING (auth.role() = 'authenticated');

-- ============================================================
-- FUNCTION: auto-update updated_at timestamp
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_user_profiles_updated_at     ON user_profiles;
DROP TRIGGER IF EXISTS update_gmail_tokens_updated_at      ON gmail_tokens;
DROP TRIGGER IF EXISTS update_applications_updated_at      ON applications;
DROP TRIGGER IF EXISTS update_referral_pipeline_updated_at ON referral_pipeline;
DROP TRIGGER IF EXISTS update_message_templates_updated_at ON message_templates;

CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_gmail_tokens_updated_at
    BEFORE UPDATE ON gmail_tokens
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_applications_updated_at
    BEFORE UPDATE ON applications
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_referral_pipeline_updated_at
    BEFORE UPDATE ON referral_pipeline
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_message_templates_updated_at
    BEFORE UPDATE ON message_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- SIGNUP HANDLER: create the user's profile row AND seed default templates.
--
-- IMPORTANT: the previous version only created message_templates and NOT a
-- user_profiles row. That meant email/password signups never appeared in
-- get_active_users(), so the scraper silently skipped them until they manually
-- saved Settings. This combined handler fixes that. It is idempotent — safe if
-- the trigger fires more than once or the script is re-run.
-- ============================================================
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    -- 1. Ensure a profile row exists so the scraper can find this user.
    INSERT INTO user_profiles (user_id, email, full_name)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'full_name', split_part(NEW.email, '@', 1))
    )
    ON CONFLICT (user_id) DO NOTHING;

    -- 2. Seed default outreach templates, but only once per user.
    IF NOT EXISTS (SELECT 1 FROM message_templates WHERE user_id = NEW.id) THEN
        INSERT INTO message_templates (user_id, name, template_type, subject_line, body, variables, is_default)
        VALUES
        (
            NEW.id,
            'LinkedIn Referral Request',
            'linkedin_referral',
            NULL,
            'Hi {name}, I hope you''re well! I came across an opening for {role} at {company} and noticed we''re connected. I''d love to learn more about the team and culture — would you be open to a brief 15-min chat? Happy to share my background in return. Thanks so much!',
            ARRAY['{name}', '{role}', '{company}'],
            TRUE
        ),
        (
            NEW.id,
            'Email Follow-Up (1 week)',
            'follow_up',
            'Following up — {role} application at {company}',
            'Hi {recruiter_name}, I wanted to follow up on my application for the {role} position submitted on {date_applied}. I remain very interested in this opportunity and would welcome the chance to discuss further. Please let me know if you need any additional information. Thank you!',
            ARRAY['{recruiter_name}', '{role}', '{company}', '{date_applied}'],
            TRUE
        ),
        (
            NEW.id,
            'Thank You — Post Interview',
            'thank_you',
            'Thank you — {role} interview',
            'Hi {interviewer_name}, Thank you for taking the time to speak with me today about the {role} position. I enjoyed learning about {specific_topic} and I''m even more excited about the opportunity. Looking forward to next steps!',
            ARRAY['{interviewer_name}', '{role}', '{specific_topic}'],
            TRUE
        );
    END IF;

    RETURN NEW;
END;
$$ language 'plpgsql' SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- ============================================================
-- BACKFILL: create profile rows for any existing auth.users that don't have
-- one yet (e.g. users who signed up before this fix). Safe to run repeatedly.
-- ============================================================
INSERT INTO user_profiles (user_id, email, full_name)
SELECT u.id, u.email, COALESCE(u.raw_user_meta_data->>'full_name', split_part(u.email, '@', 1))
FROM auth.users u
LEFT JOIN user_profiles p ON p.user_id = u.id
WHERE p.user_id IS NULL
ON CONFLICT (user_id) DO NOTHING;

-- ============================================================
-- CONSTRAINT RETROFITS — idempotent. CREATE TABLE IF NOT EXISTS can't add
-- constraints to a table that already existed from an older schema version, so
-- add them defensively here (mirrors the ADD COLUMN IF NOT EXISTS pattern).
-- ============================================================
DO $$
BEGIN
    -- Stop duplicate tracker rows when "Mark Applied" is clicked twice / in two
    -- tabs: one application per (user, job_feed job). Clean any existing dupes
    -- first so the unique index can be created.
    DELETE FROM applications a USING applications b
      WHERE a.ctid < b.ctid
        AND a.user_id = b.user_id
        AND a.job_feed_id IS NOT NULL
        AND a.job_feed_id = b.job_feed_id;

    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE schemaname = 'public' AND indexname = 'uq_applications_user_jobfeed'
    ) THEN
        CREATE UNIQUE INDEX uq_applications_user_jobfeed
            ON applications(user_id, job_feed_id)
            WHERE job_feed_id IS NOT NULL;
    END IF;

    -- Retrofit the job_feed dedupe key onto pre-existing tables (upsert_jobs
    -- relies on it via ON CONFLICT user_id,source,source_job_id).
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'job_feed_user_id_source_source_job_id_key'
    ) AND NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE schemaname = 'public' AND indexname = 'uq_job_feed_dedupe'
    ) THEN
        CREATE UNIQUE INDEX uq_job_feed_dedupe
            ON job_feed(user_id, source, source_job_id);
    END IF;
END $$;
