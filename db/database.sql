CREATE TABLE "groups" (
  "id" serial PRIMARY KEY,
  "name" text NOT NULL,
  "adults" integer NOT NULL DEFAULT 0,
  "children" integer NOT NULL DEFAULT 0,
  "infants" integer NOT NULL DEFAULT 0,
  "pets" integer NOT NULL DEFAULT 0,
  "date_range_start" date NOT NULL,
  "date_range_end" date NOT NULL,
  "price_range_min" integer DEFAULT null,
  "price_range_max" integer DEFAULT null,
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
  "nickname" text NOT NULL,
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
  "airbnb_id" text NOT NULL,
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
  PRIMARY KEY ("airbnb_id", "group_id"),
  CHECK (bnb_rating >= 0 AND bnb_rating <= 5 OR bnb_rating IS NULL),
  CHECK (price_per_night >= 0),
  CHECK (bnb_review_count >= 0),
  CHECK (min_bedrooms >= 0 OR min_bedrooms IS NULL),
  CHECK (min_beds >= 0 OR min_beds IS NULL),
  CHECK (min_bathrooms >= 0 OR min_bathrooms IS NULL)
);


CREATE TABLE "bnb_amenities" (
  "airbnb_id" text NOT NULL,
  "group_id" integer NOT NULL,
  "amenity_id" integer NOT NULL,
  PRIMARY KEY ("airbnb_id", "group_id", "amenity_id")
);


CREATE TABLE "bnb_images" (
  "airbnb_id" text NOT NULL,
  "group_id" integer NOT NULL,
  "image_url" text NOT NULL,
  PRIMARY KEY ("airbnb_id", "group_id", "image_url")
);


CREATE TABLE "votes" (
  "user_id" integer NOT NULL,
  "airbnb_id" text NOT NULL,
  "group_id" integer NOT NULL,
  "vote" smallint NOT NULL,
  "created_at" timestamptz DEFAULT (now()),
  "reason" text DEFAULT null,
  CHECK (vote >= 0 AND vote <= 3),
  PRIMARY KEY ("user_id", "airbnb_id", "group_id")
);

-- Indexes
CREATE INDEX ON "destinations" ("group_id");

CREATE INDEX ON "users" ("group_id");

CREATE INDEX ON "filter_amenities" ("user_id");

CREATE INDEX ON "filter_request" ("user_id");

CREATE INDEX ON "bnbs" ("group_id");

CREATE INDEX ON "bnbs" ("group_id", "airbnb_id");

CREATE INDEX ON "bnbs" ("group_id", "price_per_night");

CREATE INDEX ON "votes" ("airbnb_id", "group_id");

CREATE INDEX ON "votes" ("group_id");

-- Foreign Keys
ALTER TABLE "destinations" ADD FOREIGN KEY ("group_id") REFERENCES "groups" ("id");

ALTER TABLE "users" ADD FOREIGN KEY ("group_id") REFERENCES "groups" ("id");

ALTER TABLE "bnbs" ADD FOREIGN KEY ("group_id") REFERENCES "groups" ("id");

ALTER TABLE "user_filters" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("id");

ALTER TABLE "votes" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("id");

ALTER TABLE "filter_amenities" ADD FOREIGN KEY ("user_id") REFERENCES "user_filters" ("user_id");

ALTER TABLE "filter_request" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("id");

ALTER TABLE "filter_request" ADD FOREIGN KEY ("destination_id") REFERENCES "destinations" ("id");

ALTER TABLE "bnb_images" ADD FOREIGN KEY ("airbnb_id", "group_id") REFERENCES "bnbs" ("airbnb_id", "group_id");

ALTER TABLE "bnb_amenities" ADD FOREIGN KEY ("airbnb_id", "group_id") REFERENCES "bnbs" ("airbnb_id", "group_id");

ALTER TABLE "votes" ADD FOREIGN KEY ("airbnb_id", "group_id") REFERENCES "bnbs" ("airbnb_id", "group_id");

ALTER TABLE "bnbs" ADD FOREIGN KEY ("destination_id") REFERENCES "destinations" ("id");
