CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS topic_resources (
    grade INTEGER NOT NULL,
    board TEXT NOT NULL,
    subject TEXT NOT NULL,
    chapter_num INTEGER NOT NULL DEFAULT -1, -- For faster lookups. Change this if chapter_iname is mismatched. -1 if something happened
    chapter_iname TEXT NOT NULL, -- This is what should be used if chapter_num is wrong in the data build phase
    topic_iname TEXT NOT NULL, -- Topic internal name
    resource_id UUID NOT NULL DEFAULT uuid_generate_v4(), -- The resource id
    resource_type INTEGER NOT NULL, -- The resource type
    resource_url TEXT NOT NULL, -- The resource url
    resource_author TEXT NOT NULL, -- The author of a resource
    resource_metadata jsonb NOT NULL DEFAULT '{}'::jsonb, -- Any metadata such as view counts etc
    disabled BOOLEAN DEFAULT FALSE -- Whether the resource is disabled or not
);

CREATE TABLE IF NOT EXISTS users (
    username TEXT NOT NULL,
    email TEXT,
    pass TEXT NOT NULL,
    token TEXT NOT NULL,
    preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
    video_preferences JSONB NOT NULL DEFAULT '{}'::jsonb
);