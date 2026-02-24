-- Add in_egypt to processed_crime_reports
-- Three-value field representing whether the crime takes place in Egypt:
--   'نعم'       → clear visual evidence the crime is in Egypt
--   'لا'        → clear visual evidence the crime is outside Egypt
--   'غير محدد'  → insufficient visual evidence to determine location
--
-- Defaults to 'غير محدد' for existing rows (conservative — don't assume Egypt
-- for analyses that pre-date this field).

ALTER TABLE processed_crime_reports
  ADD COLUMN IF NOT EXISTS in_egypt TEXT NOT NULL DEFAULT 'غير محدد';

-- Enforce the three allowed values
ALTER TABLE processed_crime_reports
  DROP CONSTRAINT IF EXISTS chk_in_egypt;

ALTER TABLE processed_crime_reports
  ADD CONSTRAINT chk_in_egypt
    CHECK (in_egypt IN ('نعم', 'لا', 'غير محدد'));

-- Index for filtering by Egypt/non-Egypt/unknown
CREATE INDEX IF NOT EXISTS idx_reports_in_egypt
  ON processed_crime_reports(in_egypt);

-- Composite index: in_egypt + classification + score (primary dashboard filter)
CREATE INDEX IF NOT EXISTS idx_reports_in_egypt_classification
  ON processed_crime_reports(in_egypt, crime_classification, danger_score DESC);
