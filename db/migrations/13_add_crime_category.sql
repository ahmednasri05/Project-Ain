-- Add crime_category array to processed_crime_reports
-- Stores up to 2 crime category numbers (1-10) from the video analyzer.
-- Categories:
--   1. أعمال العنف والمشاجرات
--   2. أعمال البلطجة وترويع المواطنين
--   3. الاستخدام غير القانوني للأسلحة
--   4. الجرائم المرورية وتعريض الأرواح للخطر
--   5. التعدي على الآداب والقيم العامة
--   6. السرقة والنشل والسطو
--   7. تعاطي أو ترويج المواد المخدرة علناً
--   8. التحرش الجسدي واللفظي
--   9. لا شيء
--  10. اخري

ALTER TABLE processed_crime_reports
  ADD COLUMN IF NOT EXISTS crime_category INT[] NOT NULL DEFAULT '{}';

-- GIN index for array containment queries (e.g. WHERE crime_category @> ARRAY[1])
CREATE INDEX IF NOT EXISTS idx_reports_crime_category
  ON processed_crime_reports USING GIN(crime_category);
