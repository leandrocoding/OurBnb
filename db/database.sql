CREATE TABLE "groups" (
  "id" serial PRIMARY KEY,
  "name" text NOT NULL,
  "adults" integer NOT NULL DEFAULT 0,
  "children" integer NOT NULL DEFAULT 0,
  "infants" integer NOT NULL DEFAULT 0,
  "pets" integer NOT NULL DEFAULT 0,
  "date_range_start" date NOT NULL,
  "date_range_end" date NOT NULL,
  "created_at" timestamptz DEFAULT (now()),
  CHECK (date_range_start < date_range_end),
  CHECK (adults >= 0),
  CHECK (children >= 0),
  CHECK (infants >= 0),
  CHECK (pets >= 0)
);

CREATE TABLE "destinations" (
  "id" serial PRIMARY KEY,
  "group_id" integer NOT NULL,
  "location_name" text NOT NULL
);

CREATE TABLE "users" (
  "id" serial PRIMARY KEY,
  "group_id" integer NOT NULL,
  "nickname" text UNIQUE NOT NULL,
  "joined_at" timestamptz DEFAULT (now()),
  "avatar" text
);

CREATE TABLE "user_filters" (
  "user_id" integer PRIMARY KEY,
  "min_price" integer DEFAULT null,
  "max_price" integer DEFAULT null,
  "min_bedrooms" integer DEFAULT null,
  "min_beds" integer DEFAULT null,
  "min_bathrooms" integer DEFAULT null,
  "property_type" text DEFAULT null,
  "updated_at" timestamptz DEFAULT (now()),
  CHECK (min_price <= max_price OR max_price IS NULL),
  CHECK (min_price >= 0 OR min_price IS NULL),
  CHECK (max_price >= 0 OR max_price IS NULL),
  CHECK (min_bedrooms >= 0 OR min_bedrooms IS NULL),
  CHECK (min_beds >= 0 OR min_beds IS NULL),
  CHECK (min_bathrooms >= 0 OR min_bathrooms IS NULL)
);

CREATE TABLE "filter_amenities" (
  "id" serial PRIMARY KEY,
  "user_id" integer NOT NULL,
  "amenity_id" integer NOT NULL
);

CREATE TABLE "filter_request" (
  "user_id" integer,
  "destination_id" integer,
  "pages_fetched" integer NOT NULL DEFAULT 0,
  "pages_total" integer NOT NULL,
  CHECK (pages_fetched <= pages_total),
  CHECK (pages_fetched >= 0),
  CHECK (pages_total >= 0),
  PRIMARY KEY ("user_id", "destination_id")
);

CREATE TABLE "bnbs" (
  "airbnb_id" text PRIMARY KEY,
  "group_id" integer NOT NULL,
  "destination_id" integer NOT NULL,
  "title" text NOT NULL,
  "price_per_night" integer NOT NULL DEFAULT 0,
  "bnb_rating" numeric(3,2) DEFAULT null,
  "bnb_review_count" integer NOT NULL DEFAULT 0,
  "main_image_url" text DEFAULT null,
  "description" text DEFAULT null,
  "min_bedrooms" integer DEFAULT null,
  "min_beds" integer DEFAULT null,
  "min_bathrooms" integer DEFAULT null,
  "property_type" text,
  CHECK (bnb_rating >= 0 AND bnb_rating <= 5 OR bnb_rating IS NULL),
  CHECK (price_per_night >= 0),
  CHECK (bnb_review_count >= 0),
  CHECK (min_bedrooms >= 0 OR min_bedrooms IS NULL),
  CHECK (min_beds >= 0 OR min_beds IS NULL),
  CHECK (min_bathrooms >= 0 OR min_bathrooms IS NULL)
);

CREATE TABLE "bnb_amenities" (
  "airbnb_id" text,
  "amenity_id" integer,
  PRIMARY KEY ("airbnb_id", "amenity_id")
);

CREATE TABLE "bnb_images" (
  "airbnb_id" text,
  "image_url" text,
  PRIMARY KEY ("airbnb_id", "image_url")
);

CREATE TABLE "votes" (
  "user_id" integer,
  "airbnb_id" text,
  "vote" smallint NOT NULL,
  "created_at" timestamptz DEFAULT (now()),
  "reason" text DEFAULT null,
  CHECK (vote >= 0 AND vote <= 3),
  PRIMARY KEY ("user_id", "airbnb_id")
);

CREATE TABLE "bnb_queue" (
  "user_id" integer,
  "airbnb_id" text,
  "queued_at" timestamptz NOT NULL DEFAULT (now()),
  PRIMARY KEY ("user_id", "airbnb_id")
);

CREATE INDEX ON "destinations" ("group_id");

CREATE INDEX ON "users" ("group_id");

CREATE INDEX ON "filter_amenities" ("user_id");

CREATE INDEX ON "filter_request" ("user_id");

CREATE INDEX ON "bnbs" ("group_id");

CREATE INDEX ON "bnbs" ("group_id", "airbnb_id");

CREATE INDEX ON "bnbs" ("group_id", "price_per_night");

CREATE INDEX ON "votes" ("airbnb_id");

CREATE INDEX ON "bnb_queue" ("user_id", "queued_at");

ALTER TABLE "destinations" ADD FOREIGN KEY ("group_id") REFERENCES "groups" ("id");

ALTER TABLE "users" ADD FOREIGN KEY ("group_id") REFERENCES "groups" ("id");

ALTER TABLE "bnbs" ADD FOREIGN KEY ("group_id") REFERENCES "groups" ("id");

ALTER TABLE "user_filters" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("id");

ALTER TABLE "votes" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("id");

ALTER TABLE "filter_amenities" ADD FOREIGN KEY ("user_id") REFERENCES "user_filters" ("user_id");

ALTER TABLE "filter_request" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("id");

ALTER TABLE "filter_request" ADD FOREIGN KEY ("destination_id") REFERENCES "destinations" ("id");

ALTER TABLE "bnb_images" ADD FOREIGN KEY ("airbnb_id") REFERENCES "bnbs" ("airbnb_id");

ALTER TABLE "bnb_amenities" ADD FOREIGN KEY ("airbnb_id") REFERENCES "bnbs" ("airbnb_id");

ALTER TABLE "votes" ADD FOREIGN KEY ("airbnb_id") REFERENCES "bnbs" ("airbnb_id");

ALTER TABLE "bnb_queue" ADD FOREIGN KEY ("airbnb_id") REFERENCES "bnbs" ("airbnb_id");

ALTER TABLE "bnbs" ADD FOREIGN KEY ("destination_id") REFERENCES "destinations" ("id");

ALTER TABLE "bnb_queue" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("id");

-- =============================================================================
-- LEADERBOARD SCORING CONFIGURATION
-- =============================================================================
-- Adjust these values to change how listings are ranked
CREATE TABLE "scoring_config" (
  "key" text PRIMARY KEY,
  "value" integer NOT NULL,
  "description" text
);

INSERT INTO "scoring_config" ("key", "value", "description") VALUES
  ('filter_match', 10, 'Points for each user filter the listing matches'),
  ('vote_veto', -500, 'Points for a veto vote (vote=0)'),
  ('vote_ok', 10, 'Points for an ok vote (vote=1)'),
  ('vote_love', 40, 'Points for a love vote (vote=2)'),
  ('vote_super_love', 60, 'Points for a super love vote (vote=3)');

-- =============================================================================
-- LEADERBOARD VIEW
-- =============================================================================
-- Calculates scores dynamically based on filter matches and votes
CREATE OR REPLACE VIEW leaderboard_scores AS
WITH 
-- Get scoring config as columns for easy access
config AS (
  SELECT
    MAX(CASE WHEN key = 'filter_match' THEN value END) AS filter_match_pts,
    MAX(CASE WHEN key = 'vote_veto' THEN value END) AS veto_pts,
    MAX(CASE WHEN key = 'vote_ok' THEN value END) AS ok_pts,
    MAX(CASE WHEN key = 'vote_love' THEN value END) AS love_pts,
    MAX(CASE WHEN key = 'vote_super_love' THEN value END) AS super_love_pts
  FROM scoring_config
),
-- Count how many users' filters each bnb matches
filter_matches AS (
  SELECT 
    b.airbnb_id,
    b.group_id,
    COUNT(uf.user_id) AS match_count
  FROM bnbs b
  LEFT JOIN users u ON u.group_id = b.group_id
  LEFT JOIN user_filters uf ON uf.user_id = u.id
    AND (uf.min_price IS NULL OR b.price_per_night >= uf.min_price)
    AND (uf.max_price IS NULL OR b.price_per_night <= uf.max_price)
    AND (uf.min_bedrooms IS NULL OR b.min_bedrooms IS NULL OR b.min_bedrooms >= uf.min_bedrooms)
    AND (uf.min_beds IS NULL OR b.min_beds IS NULL OR b.min_beds >= uf.min_beds)
    AND (uf.min_bathrooms IS NULL OR b.min_bathrooms IS NULL OR b.min_bathrooms >= uf.min_bathrooms)
    AND (uf.property_type IS NULL OR b.property_type IS NULL OR b.property_type = uf.property_type)
  GROUP BY b.airbnb_id, b.group_id
),
-- Aggregate votes per bnb
vote_counts AS (
  SELECT
    v.airbnb_id,
    COUNT(*) FILTER (WHERE v.vote = 0) AS veto_count,
    COUNT(*) FILTER (WHERE v.vote = 1) AS ok_count,
    COUNT(*) FILTER (WHERE v.vote = 2) AS love_count,
    COUNT(*) FILTER (WHERE v.vote = 3) AS super_love_count
  FROM votes v
  INNER JOIN users u ON u.id = v.user_id
  INNER JOIN bnbs b ON b.airbnb_id = v.airbnb_id AND b.group_id = u.group_id
  GROUP BY v.airbnb_id
)
SELECT
  b.airbnb_id,
  b.group_id,
  b.title,
  b.price_per_night,
  b.bnb_rating,
  b.bnb_review_count,
  b.main_image_url,
  b.min_bedrooms,
  b.min_beds,
  b.min_bathrooms,
  b.property_type,
  COALESCE(fm.match_count, 0) AS filter_matches,
  COALESCE(vc.veto_count, 0) AS veto_count,
  COALESCE(vc.ok_count, 0) AS ok_count,
  COALESCE(vc.love_count, 0) AS love_count,
  COALESCE(vc.super_love_count, 0) AS super_love_count,
  -- Calculate total score
  (
    COALESCE(fm.match_count, 0) * c.filter_match_pts +
    COALESCE(vc.veto_count, 0) * c.veto_pts +
    COALESCE(vc.ok_count, 0) * c.ok_pts +
    COALESCE(vc.love_count, 0) * c.love_pts +
    COALESCE(vc.super_love_count, 0) * c.super_love_pts
  ) AS score
FROM bnbs b
CROSS JOIN config c
LEFT JOIN filter_matches fm ON fm.airbnb_id = b.airbnb_id
LEFT JOIN vote_counts vc ON vc.airbnb_id = b.airbnb_id;

-- Index to speed up leaderboard queries by group
CREATE INDEX idx_leaderboard_group ON bnbs (group_id);
