"use client";
import { useState } from "react";

const IconBubble = () => (
  <svg viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="currentColor" strokeWidth="1.5"
       strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 12a7 7 0 0 1-7 7H8l-4 3v-4.3A7 7 0 0 1 4 12a7 7 0 0 1 7-7h2a7 7 0 0 1 7 7Z" />
    <path d="M9 12h.01M12 12h.01M15 12h.01" />
  </svg>
);

const IconUser = () => (
  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.6"
       strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM5 20a7 7 0 0 1 14 0" />
  </svg>
);

const IconLock = () => (
  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.6"
       strokeLinecap="round" strokeLinejoin="round">
    <rect x="4" y="10" width="16" height="10" rx="2.5" />
    <path d="M8 10V7a4 4 0 0 1 8 0v3" />
  </svg>
);

const IconEye = ({ off }: { off: boolean }) => (
  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.6"
       strokeLinecap="round" strokeLinejoin="round">
    <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z" />
    <circle cx="12" cy="12" r="3" />
    {off && <path d="M4 20 20 4" />}
  </svg>
);

// ขีดสีส้มเล็ก ๆ ข้างไอคอน ให้การ์ดดูมีชีวิตตามแบบที่ออกแบบไว้
const Sparks = () => (
  <svg className="sparks" viewBox="0 0 64 64" width="64" height="64" fill="none"
       stroke="var(--accent)" strokeWidth="2.6" strokeLinecap="round" aria-hidden>
    <path d="M47 15 55 9M50 27l9-2M44 5l2-5" />
  </svg>
);

export default function Login() {
  const [u, setU] = useState("student");
  const [p, setP] = useState("student");
  const [showPw, setShowPw] = useState(false);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;
    setErr("");
    setBusy(true);
    try {
      const r = await fetch("/api/auth/login", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: u, password: p }),
      });
      if (r.ok) location.href = "/";
      else setErr("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง");
    } catch {
      setErr("ตอนนี้ระบบไม่พร้อมใช้งาน ลองใหม่อีกครั้ง");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-page">
      <img className="foliage" src="/img/foliage.png" alt="" />
      {/* จอมือถือ: ใบไม้สองฝั่ง แล้วมีมาสคอตนั่งตรงกลางด้านล่าง */}
      <img className="foliage right" src="/img/foliage.png" alt="" />
      <img className="mascot-bottom" src="/img/mascot.png" alt="มาสคอตช่วยด้วย" />

      <header className="topbar">
        <div className="brand">
          <img src="/img/logo.png" alt="" />
          <div>
            <div className="brand-name">ช่วยด้วย</div>
            <div className="brand-sub">ChuayDuay</div>
          </div>
        </div>
        <div className="topbar-tagline">เทคโนโลยีให้ชีวิตง่ายขึ้น · ช่วยด้วย อยู่ข้างคุณเสมอ</div>
      </header>

      <div className="login-body">
        <section className="hero">
          <div className="hero-kicker">YOUR IT SUPPORT BUDDY</div>
          <h1 className="hero-title">
            ปัญหาไอทีของคุณ<br />
            <span className="accent">มีเพื่อน</span><br />
            ช่วยแล้ว
          </h1>
          <p className="hero-sub">ค่อย ๆ แก้ไปด้วยกัน ทีละขั้นตอน</p>
          <div className="pill"><span className="dot" /> พร้อมช่วยคุณเสมอ</div>
          <div className="hero-script">Better Tech Together</div>
        </section>

        <section className="login-card">
          <div className="login-icon">
            <IconBubble />
            <Sparks />
          </div>
          <h2 className="login-title">ยินดีต้อนรับกลับมา</h2>
          <p className="login-note">เข้าสู่ระบบเพื่อเริ่มต้นรับความช่วยเหลือ</p>

          <form onSubmit={submit}>
            <label className="field">
              <span>ชื่อผู้ใช้</span>
              <div className="input-wrap">
                <IconUser />
                <input value={u} onChange={(e) => setU(e.target.value)} placeholder="กรอกชื่อผู้ใช้ของคุณ" />
              </div>
            </label>

            <label className="field">
              <span>รหัสผ่าน</span>
              <div className="input-wrap">
                <IconLock />
                <input value={p} onChange={(e) => setP(e.target.value)}
                       type={showPw ? "text" : "password"} placeholder="กรอกรหัสผ่าน" />
                <button type="button" className="eye" onClick={() => setShowPw((v) => !v)}
                        aria-label={showPw ? "ซ่อนรหัสผ่าน" : "แสดงรหัสผ่าน"}
                        title={showPw ? "ซ่อนรหัสผ่าน" : "แสดงรหัสผ่าน"}>
                  <IconEye off={showPw} />
                </button>
              </div>
            </label>

            <button className="btn-primary" disabled={busy}>
              {busy ? "กำลังเข้าสู่ระบบ…" : "เข้าสู่ระบบ"}
            </button>
            {err && <div className="login-error">{err}</div>}
          </form>

          <p className="login-foot">ผู้ใช้ตัวอย่างสำหรับทดสอบ: student / student</p>
        </section>

        <div className="mascot-wrap">
          <div className="speech">มีคำถาม ทักได้เลยนะครับ</div>
          <img src="/img/mascot.png" alt="มาสคอตช่วยด้วย" />
        </div>
      </div>
    </div>
  );
}
