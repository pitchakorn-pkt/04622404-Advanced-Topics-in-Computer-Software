"use client";
import { useEffect, useState } from "react";

// ป้ายภาษาคนของแต่ละ route — CONTRACT ห้ามโชว์ค่า enum ดิบให้ผู้ใช้เห็น
const ROUTE_LABEL: Record<string, string> = {
  university_rag: "ตอบจากคลังความรู้",
  general_ai: "ความรู้ทั่วไป",
  local_ai: "โมเดลในเครื่อง",
  clarify: "ขอข้อมูลเพิ่ม",
  decline: "ปฏิเสธ",
};

type Msg = { role: "user" | "assistant"; content: string; route?: string;
             sources?: any[]; latency_ms?: number };

export default function Chat() {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [sid, setSid] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/auth/me").then((r) => { if (r.status === 401) location.href = "/login"; });
  }, []);

  async function send() {
    const q = text.trim();
    if (!q || busy) return;
    setText("");
    setMsgs((m) => [...m, { role: "user", content: q }]);   // แสดงทันทีไม่ต้องรอ server
    setBusy(true);
    try {
      const r = await fetch("/api/chat", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sid, message: q, file_ids: [] }),
      });
      if (r.status === 401) { location.href = "/login"; return; }
      const d = await r.json();
      setSid(d.session_id);
      setMsgs((m) => [...m, { role: "assistant", content: d.answer, route: d.route,
                              sources: d.sources, latency_ms: d.latency_ms }]);
    } catch {
      setMsgs((m) => [...m, { role: "assistant", content: "ตอนนี้ระบบไม่พร้อมใช้งาน ลองใหม่อีกครั้ง" }]);
    } finally { setBusy(false); }
  }

  return (
    <main style={{ maxWidth: 760, margin: "0 auto", padding: 16, minHeight: "100vh",
                   display: "flex", flexDirection: "column" }}>
      <h1 style={{ fontSize: 22 }}>ช่วยด้วย</h1>

      <div style={{ flex: 1, display: "grid", gap: 12, alignContent: "start" }}>
        {msgs.map((m, i) => (
          <div key={i} style={{ justifySelf: m.role === "user" ? "end" : "start", maxWidth: "85%" }}>
            <div style={{ padding: "10px 14px", borderRadius: 12, whiteSpace: "pre-wrap",
                          background: m.role === "user" ? "#e91e63" : "#161a22" }}>
              {m.content}
            </div>
            {m.role === "assistant" && m.route && (
              <div style={{ fontSize: 12, opacity: 0.6, marginTop: 4 }}>
                {ROUTE_LABEL[m.route] ?? m.route}
                {m.latency_ms != null && ` · ${m.latency_ms} ms`}
              </div>
            )}
            {/* 4 ใน 5 route คืน sources ว่าง — ต้องไม่โชว์หัวข้อเปล่า */}
            {!!m.sources?.length && (
              <ol style={{ fontSize: 13, opacity: 0.8, marginTop: 6 }}>
                {m.sources.map((s: any) => (
                  <li key={s.ref}>{s.url ? <a href={s.url} style={{ color: "#7bb3ff" }}>{s.title}</a> : s.title}</li>
                ))}
              </ol>
            )}
          </div>
        ))}
        {busy && <div style={{ opacity: 0.5 }}>กำลังคิด…</div>}
      </div>

      <div style={{ display: "flex", gap: 8, paddingTop: 12 }}>
        <input value={text} onChange={(e) => setText(e.target.value)}
               onKeyDown={(e) => e.key === "Enter" && send()}
               placeholder="พิมพ์คำถาม เช่น ต่อไวไฟไม่ได้ ควรทำยังไง"
               style={{ flex: 1, padding: "12px 14px", borderRadius: 10,
                        border: "1px solid #2a2f3a", background: "#161a22", color: "#e6e6e6" }} />
        <button onClick={send} disabled={busy}
                style={{ padding: "12px 20px", borderRadius: 10, border: "none",
                         background: busy ? "#555" : "#e91e63", color: "#fff",
                         cursor: busy ? "default" : "pointer", fontWeight: 600 }}>ส่ง</button>
      </div>
    </main>
  );
}
