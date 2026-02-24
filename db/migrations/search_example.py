import sys
import os

# Ensure the parent directory containing db/ is in sys.path so penal_code_search can be imported reliably.
current_dir = os.path.dirname(os.path.abspath(__file__))
db_dir = os.path.abspath(os.path.join(current_dir, ".."))
if db_dir not in sys.path:
    sys.path.insert(0, db_dir)

import penal_code_search

# أمثلة: وصف مخالفات أو انتهاكات لقانون العقوبات العربي

if __name__ == "__main__":
    arabic_violations = [
        "قيادة السيارة بدون رخصة",
        "الاعتداء على موظف عام أثناء تأدية عمله",
        "السرقة تحت تهديد السلاح",
        "إلقاء القمامة في الطرق العامة"
    ]

    with open("search_result.txt", "w", encoding="utf-8") as f:
        for violation in arabic_violations:
            f.write(f"\nبحث عن مخالفات مشابهة لـ: {violation}\n")
            results = penal_code_search.search_penal_code(
                query=violation,
                limit=3,
                similarity_threshold=0.25  # يمكن ضبط مستوى التشابه المطلوب
            )
            for i, r in enumerate(results, 1):
                f.write(f"\nمطابقة #{i}\n")
                f.write(f"العنوان: {r.get('chapter_title', '')}\n")
                f.write(f"النص: {r.get('article_text', '')[:120]} ...\n")
                f.write(f"درجة التشابه: {round(r.get('similarity', 0), 3)}\n")
