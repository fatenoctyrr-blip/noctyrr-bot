CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    username VARCHAR(255),
    first_name VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS channels (
    id BIGSERIAL PRIMARY KEY,
    telegram_channel_id BIGINT NOT NULL UNIQUE,
    owner_id BIGINT NOT NULL REFERENCES users(id),
    title VARCHAR(255),
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS battle_contests (
    id BIGSERIAL PRIMARY KEY,
    channel_id BIGINT NOT NULL REFERENCES channels(id),
    task TEXT NOT NULL,
    target_count INTEGER,
    end_time TIMESTAMPTZ,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    post_chat_id BIGINT,
    post_message_id BIGINT,
    winner_id BIGINT REFERENCES users(id),
    created_by BIGINT NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS battle_contest_participants (
    id BIGSERIAL PRIMARY KEY,
    contest_id BIGINT NOT NULL REFERENCES battle_contests(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(id),
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (contest_id, user_id)
);

CREATE TABLE IF NOT EXISTS point_contests (
    id BIGSERIAL PRIMARY KEY,
    channel_id BIGINT NOT NULL REFERENCES channels(id),
    gift TEXT NOT NULL,
    media_file_id VARCHAR(255),
    weights_json JSONB NOT NULL DEFAULT '{"reaction":1,"stars":5,"boost":1,"comment":1,"purchased":1}'::jsonb,
    end_time TIMESTAMPTZ,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    post_chat_id BIGINT,
    post_message_id BIGINT,
    winner_id BIGINT REFERENCES users(id),
    created_by BIGINT NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS point_entries (
    id BIGSERIAL PRIMARY KEY,
    contest_id BIGINT NOT NULL REFERENCES point_contests(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(id),
    reaction_points INTEGER NOT NULL DEFAULT 0,
    stars_points INTEGER NOT NULL DEFAULT 0,
    boost_points INTEGER NOT NULL DEFAULT 0,
    comment_points INTEGER NOT NULL DEFAULT 0,
    purchased_points INTEGER NOT NULL DEFAULT 0,
    UNIQUE (contest_id, user_id)
);

CREATE TABLE IF NOT EXISTS group_games (
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    type VARCHAR(32) NOT NULL,
    config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_by BIGINT NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS subscription_requirements (
    id BIGSERIAL PRIMARY KEY,
    contest_id BIGINT NOT NULL,
    resource_chat_id BIGINT NOT NULL,
    resource_title VARCHAR(255),
    required_referrals INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS admin_overrides (
    id BIGSERIAL PRIMARY KEY,
    contest_id BIGINT NOT NULL,
    grand_admin_id BIGINT NOT NULL,
    chosen_winner_id BIGINT NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS referrals (
    id BIGSERIAL PRIMARY KEY,
    referrer_id BIGINT NOT NULL REFERENCES users(id),
    referred_id BIGINT NOT NULL UNIQUE REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_battle_contests_status ON battle_contests(status);
CREATE INDEX IF NOT EXISTS idx_point_contests_status ON point_contests(status);
CREATE INDEX IF NOT EXISTS idx_group_games_chat_status ON group_games(chat_id, status);