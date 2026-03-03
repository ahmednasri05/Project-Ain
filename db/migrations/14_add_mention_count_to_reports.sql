-- Denormalize mention_count into processed_crime_reports
-- Copied from raw_instagram_reels at save time to enable direct
-- sort/filter in dashboard queries without a join.

ALTER TABLE processed_crime_reports
  ADD COLUMN IF NOT EXISTS mention_count INT NOT NULL DEFAULT 1;

-- Index for sorting by mention count
CREATE INDEX IF NOT EXISTS idx_reports_mention_count
  ON processed_crime_reports(mention_count DESC);
