"""เทรนโมเดลจำแนกหมวดคำถาม (Local AI) จาก data/intents.csv
TF-IDF (word-level ตัดคำด้วย pythainlp ผ่าน nlp_utils.thai_tokenizer + char-level
2-4 ตัวอักษร) + LinearSVC

หมายเหตุสำคัญ: thai_tokenizer อยู่ใน nlp_utils.py (ไม่ใช่ไฟล์นี้) เพราะ
TfidfVectorizer เก็บ reference ไปยังฟังก์ชันตรงๆ ตอน joblib.dump — ถ้านิยาม
ไว้ในไฟล์นี้ (module จะกลายเป็น __main__ ตอนรัน `python train.py` ตรงๆ)
app/main.py ที่ joblib.load ทีหลังจากคนละ process จะหาฟังก์ชันไม่เจอ

รันด้วย:
    python train.py
ผลลัพธ์:
    - พิมพ์ CV accuracy (5-fold, ตัวชี้วัดหลักตาม DoD), single-split accuracy
      แบบละเอียด และ confusion matrix ออกหน้าจอ
    - เซฟโมเดล + vectorizer ไว้ที่ models/intent_v1.joblib
"""
import csv
import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC

from nlp_utils import thai_tokenizer  # ใช้ร่วมกับ app/main.py — ดูเหตุผลใน nlp_utils.py

HERE = Path(__file__).parent
CSV_PATH = HERE / "data" / "intents.csv"
MODEL_DIR = HERE / "models"
MODEL_PATH = MODEL_DIR / "intent_v1.joblib"

RANDOM_STATE = 42
TEST_SIZE = 0.2
CV_FOLDS = 5  # จำนวน fold สำหรับ cross-validation


def load_dataset(csv_path: Path) -> tuple[list[str], list[str]]:
    if not csv_path.exists():
        sys.exit(f"ไม่พบไฟล์ {csv_path} — ต้องมี data/intents.csv ก่อนรัน train.py")
    texts, labels = [], []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            texts.append(row["text"])
            labels.append(row["label"])
    return texts, labels


def build_vectorizer() -> FeatureUnion:
    """รวม word-level TF-IDF (ตัดคำด้วย pythainlp) + char-level TF-IDF (2-4 ตัวอักษร)
    char-level ช่วยจับความคล้ายของคำที่ตัดคำผิด/ไม่สมบูรณ์ และรูปแบบผันคำที่คล้ายกัน
    """
    word_vec = TfidfVectorizer(
        tokenizer=thai_tokenizer,
        token_pattern=None,
        ngram_range=(1, 2),
        min_df=1,
    )
    char_vec = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(2, 4),
        min_df=2,
    )
    return FeatureUnion([("word", word_vec), ("char", char_vec)])


def build_pipeline() -> Pipeline:
    """สร้าง vectorizer (word+char) + LinearSVC pipeline เดียวกันทั้งตอน CV และตอนเทรนจริง
    LinearSVC มักให้ผลดีกว่า LogisticRegression บนฟีเจอร์ TF-IDF แบบ sparse
    """
    return Pipeline([
        ("features", build_vectorizer()),
        ("clf", LinearSVC(
            class_weight="balanced",
            random_state=RANDOM_STATE,
            max_iter=10000,
        )),
    ])


def main() -> None:
    texts, labels = load_dataset(CSV_PATH)
    print(f"โหลด dataset แล้ว: {len(texts)} ตัวอย่าง, {len(set(labels))} หมวด")

    # --- Cross-validation: ตัวชี้วัดหลักตาม Definition of Done ---
    # การแบ่ง train/test แค่ครั้งเดียว (ด้านล่าง) มี test set เล็กมาก (~20%)
    # ทำให้ accuracy เด้งขึ้นลงได้ง่ายเวลาข้อมูลเปลี่ยนแค่เล็กน้อย
    # cross_val_score รันแบ่งข้อมูลคนละมุม CV_FOLDS รอบแล้วเฉลี่ยผล จึงนิ่งและ
    # สะท้อนความแม่นยำจริงของโมเดลได้แม่นกว่า
    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    cv_scores = cross_val_score(build_pipeline(), texts, labels, cv=cv, scoring="accuracy")
    cv_mean, cv_std = cv_scores.mean(), cv_scores.std()

    print("\n" + "=" * 60)
    print(f"CROSS-VALIDATION ACCURACY ({CV_FOLDS}-fold): "
          f"{cv_mean:.2%} (+/- {cv_std:.2%})")
    print("แต่ละ fold:", ", ".join(f"{s:.2%}" for s in cv_scores))
    print("=" * 60)

    # --- Single train/test split: ใช้สำหรับดู confusion matrix แบบละเอียด
    #     และเทรนโมเดลตัวจริงที่จะเซฟไว้ใช้งาน (ไม่ใช้เป็นตัวชี้วัด DoD แล้ว) ---
    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=labels,  # แบ่งให้สัดส่วนแต่ละหมวดเท่ากันทั้ง train/test
    )

    vectorizer = build_vectorizer()
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)

    clf = LinearSVC(
        class_weight="balanced",  # กันหมวดที่มีตัวอย่างน้อยกว่าถูกมองข้าม
        random_state=RANDOM_STATE,
        max_iter=10000,
    )
    clf.fit(X_train_vec, y_train)

    y_pred = clf.predict(X_test_vec)
    acc = accuracy_score(y_test, y_pred)

    print(f"\n(single split เดิม สำหรับดูรายละเอียด — ไม่ใช่ตัวชี้วัด DoD): "
          f"accuracy = {acc:.2%}")
    print("\nClassification report:")
    print(classification_report(y_test, y_pred, zero_division=0))
    print("Confusion matrix (แถว=จริง, คอลัมน์=ทำนาย):")
    labels_sorted = sorted(set(labels))
    cm = confusion_matrix(y_test, y_pred, labels=labels_sorted)
    header = " " * 22 + " ".join(f"{l[:10]:>10}" for l in labels_sorted)
    print(header)
    for label, row in zip(labels_sorted, cm):
        print(f"{label[:20]:<22}" + " ".join(f"{v:>10}" for v in row))

    MODEL_DIR.mkdir(exist_ok=True)
    joblib.dump({"vectorizer": vectorizer, "classifier": clf}, MODEL_PATH)
    print(f"\nเซฟโมเดลแล้วที่ {MODEL_PATH}")

    print("\n" + "=" * 60)
    print(f"สรุปตาม Definition of Done: CV accuracy เฉลี่ย {CV_FOLDS}-fold = "
          f"{cv_mean:.2%} (+/- {cv_std:.2%})")
    print("=" * 60)

    if cv_mean < 0.80:
        print(
            "\n⚠️  CV accuracy เฉลี่ยต่ำกว่า 80% ตาม Definition of Done — "
            "ลองเพิ่มตัวอย่างในหมวดที่ทำนายผิดบ่อย (ดู confusion matrix ด้านบน) "
            "ใน data/intents.csv แล้วรันใหม่"
        )
    else:
        print(f"\n✅ ผ่าน Definition of Done (CV accuracy เฉลี่ย {cv_mean:.2%} ≥ 80%)")


if __name__ == "__main__":
    main()