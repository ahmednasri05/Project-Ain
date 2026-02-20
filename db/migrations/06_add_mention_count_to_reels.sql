-- Add mention_count to raw_instagram_reels
-- Increments every time the same video is submitted again,
-- either by re-entering the same shortcode or via a repost with a different shortcode.
-- Starts at 1 (the original submission). Used later as an urgency signal.

ALTER TABLE raw_instagram_reels
  ADD COLUMN IF NOT EXISTS mention_count INT NOT NULL DEFAULT 1;

-- Stored procedure for atomic increment (called from the pipeline)
CREATE OR REPLACE FUNCTION increment_reel_mention_count(reel_shortcode TEXT)
RETURNS VOID AS $$
  UPDATE raw_instagram_reels
    SET mention_count = mention_count + 1
    WHERE shortcode = reel_shortcode;
$$ LANGUAGE SQL;
