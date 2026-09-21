"""วิเคราะห์ error ของ intent classifier แบบละเอียด — เสริมจาก train.py
รันด้วย: python analyze_errors.py  (รันจากโฟลเดอร์เดียวกับ train.py)

พิมพ์ 3 ส่วน:
  1. จำนวนแถวต่อคลาสใน data/intents.csv (ทั้งชุด ไม่ใช่แค่ test split)
  2. คู่ที่สับสนบ่อย (จริง -> ทาย) เรียงจากมากไปน้อย จาก single train/test split
  3. รายการข้อความจริงที่ทำนายผิด เฉพาะ general_other, out_of_scope, hardware_media
     พร้อม label จริง / ที่ทายได้ / confidence
"""
from collections import Counter

from sklearn.model_selection import train_test_split

from train import CSV_PATH, RANDOM_STATE, TEST_SIZE, build_classifier, build_vectorizer, load_dataset

FOCUS_LABELS = {"general_other", "out_of_scope", "hardware_media"}


def main() -> None:
    texts, labels = load_dataset(CSV_PATH)

    # --- 1) จำนวนแถวต่อคลาส (ทั้งชุดข้อมูล) ---
    print("=" * 60)
    print("1) จำนวนแถวต่อคลาสใน data/intents.csv")
    print("=" * 60)
    counts = Counter(labels)
    for label, n in sorted(counts.items()):
        print(f"  {label:<20} {n}")
    print(f"  {'รวม':<20} {len(labels)}")

    # --- เทรนด้วย single split เดียวกับ train.py เพื่อดู error ---
    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=labels,
    )
    vectorizer = build_vectorizer()
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)
    clf = build_classifier()
    clf.fit(X_train_vec, y_train)

    y_pred = clf.predict(X_test_vec)
    probs = clf.predict_proba(X_test_vec)
    classes = list(clf.classes_)

    # --- 2) คู่ที่สับสนบ่อย ---
    confusions = Counter()
    for true, pred in zip(y_test, y_pred):
        if true != pred:
            confusions[(true, pred)] += 1

    print("\n" + "=" * 60)
    print("2) คู่ที่สับสนบ่อย (จริง -> ทาย) เรียงจากมากไปน้อย")
    print("=" * 60)
    for (true, pred), n in confusions.most_common():
        print(f"  {true} -> {pred}: {n} ข้อ")

    # --- 3) รายการข้อความที่ทำนายผิด เฉพาะ 3 หมวดที่สนใจ ---
    print("\n" + "=" * 60)
    print("3) ข้อความที่ทำนายผิด เฉพาะ general_other / out_of_scope / hardware_media")
    print("=" * 60)
    for text, true, pred, prob_row in zip(X_test, y_test, y_pred, probs):
        if true != pred and true in FOCUS_LABELS:
            score = prob_row[classes.index(pred)]
            print(f"  [{true} -> {pred}, score={score:.2f}] {text}")


if __name__ == "__main__":
    main()
