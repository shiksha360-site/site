CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS topic_resources (
    grade INTEGER NOT NULL,
    board TEXT NOT NULL,
    subject TEXT NOT NULL,
    chapter_num INTEGER NOT NULL DEFAULT -1, -- For faster lookups. Change this if chapter_iname is mismatched. -1 if something happened
    chapter_iname TEXT NOT NULL, -- This is what should be used if chapter_num is wrong in the data build phase
    topic_iname TEXT NOT NULL, -- Topic internal name
    subtopic_parent TEXT NOT NULL DEFAULt -1, -- Subtopic parent iname
    resource_id UUID NOT NULL DEFAULT uuid_generate_v4(), -- The resource id
    resource_type INTEGER NOT NULL, -- The resource type
    resource_title TEXT NOT NULL, -- Resource title
    resource_description TEXT, -- Resource description (if you want to provide that)
    resource_url TEXT NOT NULL, -- The resource url
    resource_author TEXT NOT NULL, -- The author of a resource
    resource_icon TEXT NOT NULL, -- The resource icon
    resource_metadata jsonb NOT NULL DEFAULT '{}'::jsonb, -- Any metadata such as view counts etc
    resource_lang text not null default 'en', -- The language
    disabled BOOLEAN DEFAULT FALSE -- Whether the resource is disabled or not
);

CREATE TABLE IF NOT EXISTS users (
    username TEXT NOT NULL,
    user_id UUID NOT NULL DEFAULT uuid_generate_v4(),
    email TEXT,
    pass TEXT NOT NULL,
    token TEXT NOT NULL,
    preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
    video_preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
    login_attempts INTEGER DEFAULT 0
);
