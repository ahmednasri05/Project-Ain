-- Add source_shortcode to instagram_comments
-- Tracks which reel a comment physically appeared on.
-- For original reels: source_shortcode = reel_shortcode
-- For reposts: reel_shortcode = original shortcode (incident FK),
--              source_shortcode = the repost's shortcode (where it appeared)

ALTER TABLE instagram_comments
  ADD COLUMN IF NOT EXISTS source_shortcode TEXT;

-- Backfill existing rows: source = reel for all pre-existing comments
UPDATE instagram_comments
  SET source_shortcode = reel_shortcode
  WHERE source_shortcode IS NULL;

CREATE INDEX IF NOT EXISTS idx_comments_source_shortcode
  ON instagram_comments(source_shortcode);
