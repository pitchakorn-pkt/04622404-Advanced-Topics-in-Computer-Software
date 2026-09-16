"use client";
import { useState } from "react";

export default function Login() {
  const [u, setU] = useState("student");
  const [p, setP] = useState("student");
  const [err, setErr] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    const r = await fetch("/api/auth/login", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: u, password: p }),
    });
    if (r.ok) location.href = "/";
    else setErr("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง");
  }

  return (
    <main style={{ maxWidth: 360, margin: "15vh auto", padding: 16 }}>
      <h1 style={{ fontSize: 28, marginBottom: 4 }}>ช่วยด้วย</h1>
      <p style={{ opacity: 0.6, marginTop: 0 }}>ผู้ช่วยแก้ปัญหามือถือและคอมพิวเตอร์</p>
      <form onSubmit={submit} style={{ display: "grid", gap: 10, marginTop: 24 }}>
        <input value={u} onChange={(e) => setU(e.target.value)} placeholder="ชื่อผู้ใช้" style={inp} />
        <input value={p} onChange={(e) => setP(e.target.value)} type="password" placeholder="รหัสผ่าน" style={inp} />
        <button style={btn}>เข้าสู่ระบบ</button>
        {err && <div style={{ color: "#ff6b6b" }}>{err}</div>}
      </form>
      <p style={{ opacity: 0.45, fontSize: 13, marginTop: 20 }}>ผู้ใช้ตัวอย่างสำหรับทดสอบ: student / student</p>
    </main>
  );
}
const inp = { padding: "10px 12px", borderRadius: 8, border: "1px solid #2a2f3a", background: "#161a22", color: "#e6e6e6" };
const btn = { ...inp, background: "#e91e63", border: "none", cursor: "pointer", fontWeight: 600 };
