-- Add crime_classification to processed_crime_reports
-- Stores the Egyptian Penal Code classification determined by the video analyzer.
-- Possible values: 'جناية' (felony) | 'جنحة' (misdemeanor) | 'مخالفة' (violation) | 'لا شيء' (none)

ALTER TABLE processed_crime_reports
  ADD COLUMN IF NOT EXISTS crime_classification TEXT;

-- Index for filtering/grouping by legal classification in dashboard queries
CREATE INDEX IF NOT EXISTS idx_reports_crime_classification
  ON processed_crime_reports(crime_classification);

-- Composite index: classification + danger_score + time (common dashboard pattern)
CREATE INDEX IF NOT EXISTS idx_reports_classification_score
  ON processed_crime_reports(crime_classification, danger_score DESC, processed_at DESC);

-- Add a check constraint to enforce the four allowed values (NULL allowed for legacy rows)
ALTER TABLE processed_crime_reports
  DROP CONSTRAINT IF EXISTS chk_crime_classification;

ALTER TABLE processed_crime_reports
  ADD CONSTRAINT chk_crime_classification
    CHECK (crime_classification IN ('جناية', 'جنحة', 'مخالفة', 'لا شيء') OR crime_classification IS NULL);
