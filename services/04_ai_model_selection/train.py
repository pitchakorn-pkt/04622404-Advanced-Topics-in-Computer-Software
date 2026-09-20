"""เทรนโมเดลจำแนกหมวดคำถาม (Local AI) จาก data/intents.csv
TF-IDF (word-level ตัดคำด้วย pythainlp ผ่าน nlp_utils.thai_tokenizer + char-level
2-4 ตัวอักษร) + LinearSVC ครอบด้วย CalibratedClassifierCV เพื่อให้ได้
predict_proba() ที่ใช้งานได้จริง (ดูหมายเหตุ CALIBRATION ด้านล่าง)

หมายเหตุสำคัญ: thai_tokenizer อยู่ใน nlp_utils.py (ไม่ใช่ไฟล์นี้) เพราะ
TfidfVectorizer เก็บ reference ไปยังฟังก์ชันตรงๆ ตอน joblib.dump — ถ้านิยาม
ไว้ในไฟล์นี้ (module จะกลายเป็น __main__ ตอนรัน `python train.py` ตรงๆ)
app/main.py ที่ joblib.load ทีหลังจากคนละ process จะหาฟังก์ชันไม่เจอ

หมายเหตุ CALIBRATION (สำคัญมาก): LinearSVC เพียวๆ ไม่มี predict_proba —
เดิมใช้ decision_function() แล้วแปลงด้วย softmax เอง (pseudo-probability)
แต่ค่าที่ได้ต่ำเกินไปมาก (สูงสุดวัดได้ 0.36) ทำให้ CONTRACT ที่กำหนดให้ router
เชื่อผล classifier เมื่อ score >= 0.75 ไม่มีวันถูกใช้งานจริง (พบจาก code review
PR #8) แก้โดยครอบ LinearSVC ด้วย CalibratedClassifierCV (Platt scaling ผ่าน
cv=5) แล้วใช้ .predict_proba() ตรงๆ ซึ่งให้ค่าที่ใช้งานได้จริงตามเกณฑ์ 0.75

หมายเหตุ FULL-DATA FIT (สำคัญ): โมเดลที่เซฟลง models/intent_v1.joblib เทรน
ด้วยข้อมูลทั้งหมด 100% (ไม่ใช่แค่ 80% ที่ train_test_split กันไว้) — ส่วน
train/test split ยังใช้วัด accuracy/confusion matrix ตามปกติ (วัดบนข้อมูลที่
โมเดลไม่เคยเห็น) แต่โมเดลตัวจริงที่ deploy ควร fit ด้วยทุกแถวที่มี (พบจาก
code review PR #8)

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
from sklearn.calibration import CalibratedClassifierCV
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
CALIBRATION_CV_FOLDS = 5  # จำนวน fold ภายในสำหรับ CalibratedClassifierCV


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


def build_classifier() -> CalibratedClassifierCV:
    """LinearSVC ครอบด้วย CalibratedClassifierCV ให้ได้ predict_proba() ที่ใช้งานได้จริง
    (ดูหมายเหตุ CALIBRATION ที่หัวไฟล์ — เดิมใช้ softmax เอง แต่ score ต่ำเกินไป
    จนไม่ผ่านเกณฑ์ 0.75 ของ CONTRACT เลยแม้แต่ข้อเดียว)
    """
    base_clf = LinearSVC(
        class_weight="balanced",
        random_state=RANDOM_STATE,
        max_iter=10000,
    )
    return CalibratedClassifierCV(base_clf, method="sigmoid", cv=CALIBRATION_CV_FOLDS)


def build_pipeline() -> Pipeline:
    """สร้าง vectorizer (word+char) + calibrated LinearSVC pipeline เดียวกัน
    ทั้งตอน CV และตอนเทรนจริง LinearSVC มักให้ผลดีกว่า LogisticRegression
    บนฟีเจอร์ TF-IDF แบบ sparse
    """
    return Pipeline([
        ("features", build_vectorizer()),
        ("clf", build_classifier()),
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

    clf = build_classifier()
    clf.fit(X_train_vec, y_train)

    y_pred = clf.predict(X_test_vec)
    y_proba = clf.predict_proba(X_test_vec)
    acc = accuracy_score(y_test, y_pred)

    print(f"\n(single split เดิม สำหรับดูรายละเอียด — ไม่ใช่ตัวชี้วัด DoD): "
          f"accuracy = {acc:.2%}")

    # เช็คตรงตาม CONTRACT: router จะเชื่อผล classifier เมื่อ score >= 0.75 เท่านั้น
    # (ตัวเลขนี้คือสิ่งที่ code review ของ PR #8 ชี้ว่าพังตั้งแต่ตอน softmax เอง)
    ROUTER_THRESHOLD = 0.75
    top_scores = y_proba.max(axis=1)
    above_threshold = top_scores >= ROUTER_THRESHOLD
    n_above = int(above_threshold.sum())
    if n_above:
        acc_above = accuracy_score(
            np.array(y_test)[above_threshold], np.array(y_pred)[above_threshold]
        )
    else:
        acc_above = 0.0
    print(
        f"เช็คเกณฑ์ router (score >= {ROUTER_THRESHOLD}): "
        f"{n_above}/{len(y_test)} ข้อถึงเกณฑ์ ({n_above / len(y_test):.1%}), "
        f"ถูก {acc_above:.1%} ในกลุ่มที่ถึงเกณฑ์"
    )

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

    # สำคัญ: โมเดลที่เซฟไว้ใช้งานจริงต้อง fit ด้วยข้อมูลทั้งหมด 100% ไม่ใช่แค่
    # ส่วน train (80%) ที่ใช้ประเมินผลด้านบน — 20% ที่กันไว้เป็น test set ก็มี
    # ข้อมูลมีค่าที่ไม่ควรทิ้งไปตอนเทรนโมเดลตัวจริง (พบจาก code review PR #8)
    # ตัวเลข accuracy/confusion matrix ด้านบนยังใช้ split เดิมได้ตามปกติ เพราะ
    # เป็นการวัดผลบนข้อมูลที่โมเดลไม่เคยเห็น แต่โมเดลที่ deploy จริงควรใช้ข้อมูล
    # ทุกแถวที่มี
    print("\n" + "=" * 60)
    print("เทรนโมเดลตัวจริงที่จะเซฟด้วยข้อมูลทั้งหมด 100% (ไม่ใช่แค่ 80% ที่ split ไว้เทส)")
    print("=" * 60)
    final_vectorizer = build_vectorizer()
    final_clf = build_classifier()
    final_clf.fit(final_vectorizer.fit_transform(texts), labels)

    joblib.dump({"vectorizer": final_vectorizer, "classifier": final_clf}, MODEL_PATH)
    print(f"เซฟโมเดลแล้วที่ {MODEL_PATH}")

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