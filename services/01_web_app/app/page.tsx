"use client";
import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import remarkGfm from "remark-gfm";

// ป้ายภาษาคนของแต่ละ route — CONTRACT ห้ามโชว์ค่า enum ดิบให้ผู้ใช้เห็น
const ROUTE_LABEL: Record<string, string> = {
  university_rag: "ตอบจากคลังความรู้",
  general_ai: "ความรู้ทั่วไป",
  local_ai: "โมเดลในเครื่อง",
  clarify: "ขอข้อมูลเพิ่ม",
  decline: "ปฏิเสธ",
};

// ป้ายภาษาคนของชั้นที่ตัดสินใจ (decided_at_layer ใน Trace)
const LAYER_LABEL: Record<string, string> = {
  guard: "ตัวกรองเบื้องต้น",
  rules: "กฎที่ตั้งไว้",
  classifier: "ตัวจำแนกประเภท",
  llm: "โมเดลภาษา (LLM)",
};

const CHAT_TIMEOUT_MS = 90_000; // web→api เพดาน 90 วินาทีตาม CONTRACT §0

type TraceStep = { name: string; ms: number };
type Trace = { decided_at_layer?: string; steps?: TraceStep[]; reasoning?: string };
type Msg = { role: "user" | "assistant"; content: string; route?: string;
             sources?: any[]; latency_ms?: number; confidence?: number;
             trace?: Trace; reasoning?: string; message_id?: string;
             rating?: 1 | -1 | null; isError?: boolean; retryText?: string };
type SessionSummary = { session_id: string; title?: string; updated_at?: string };

// แทนที่ [1] [2] ในคำตอบด้วยลิงก์ที่เลื่อนไปหา source ตัวนั้น
// ผูกกับ msgIndex เพื่อไม่ให้ id ชนกันข้ามข้อความ
function linkifyRefs(text: string, msgIndex: number) {
  return text.replace(/\[(\d+)\]/g, (_m, n) => `[[${n}]](#src-${msgIndex}-${n})`);
}

export default function Chat() {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [sid, setSid] = useState<string | null>(null);
  const [openTrace, setOpenTrace] = useState<Set<number>>(new Set());
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  useEffect(() => {
    fetch("/api/auth/me").then((r) => { if (r.status === 401) location.href = "/login"; });
    loadSessions();
  }, []);

  async function loadSessions() {
    try {
      const r = await fetch("/api/sessions");
      if (!r.ok) return;
      const d = await r.json();
      setSessions(d.sessions ?? []);
    } catch {
      // โหลดรายการ session ไม่สำเร็จ ไม่ต้องเด้ง error แค่ sidebar จะว่างไปก่อน
    }
  }

  function newChat() {
    setSid(null);
    setMsgs([]);
    setOpenTrace(new Set());
  }

  // session ที่ยังไม่มีข้อความ (พึ่งสร้าง) จะได้ messages: [] แบบ 200 ปกติ ไม่ใช่ error (CONTRACT §6 ข้อ 3)
  async function openSession(id: string) {
    setLoadingHistory(true);
    setOpenTrace(new Set());
    try {
      const r = await fetch(`/api/history/${id}`);
      if (r.status === 401) { location.href = "/login"; return; }
      const d = await r.json();
      setSid(d.session_id ?? id);
      const loaded: Msg[] = (d.messages ?? []).map((mm: any) => ({
        role: mm.role, content: mm.content, route: mm.route, sources: mm.sources,
        message_id: mm.message_id, rating: mm.rating ?? null,
      }));
      setMsgs(loaded);
    } catch {
      // โหลดประวัติไม่สำเร็จ ปล่อยให้หน้าจอใช้งานต่อได้ ไม่เด้ง error
    } finally {
      setLoadingHistory(false);
    }
  }

  function toggleTrace(i: number) {
    setOpenTrace((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i); else next.add(i);
      return next;
    });
  }

  // ผู้ใช้กด 👍👎 ได้ทันทีหลังได้คำตอบ ไม่ต้องรอ — ฝั่งหลังบ้านรองรับกรณีนี้ไว้แล้ว (CONTRACT §6 ข้อ 4)
  async function rate(i: number, rating: 1 | -1) {
    const target = msgs[i];
    if (!target?.message_id) return;
    setMsgs((prev) => prev.map((m, idx) => (idx === i ? { ...m, rating } : m))); // โชว์ผลทันที
    try {
      await fetch("/api/feedback", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message_id: target.message_id, rating }),
      });
    } catch {
      // โหวตไม่ผ่านก็ไม่ต้องเด้ง error รบกวนผู้ใช้ ปล่อยให้ลองกดใหม่ได้เอง
    }
  }

  // ยิงคำถามจริง แยกออกมาจาก send() เพื่อให้ปุ่ม "ลองใหม่" เรียกซ้ำด้วยคำถามเดิมได้
  async function runQuery(q: string) {
    setBusy(true);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), CHAT_TIMEOUT_MS);
    try {
      const r = await fetch("/api/chat", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sid, message: q, file_ids: [] }),
        signal: controller.signal,
      });

      if (r.status === 401) { location.href = "/login"; return; }

      if (r.status === 429) {
        setMsgs((m) => [...m, { role: "assistant",
          content: "ถามถี่เกินไป รอสักครู่แล้วลองใหม่อีกครั้ง", isError: true }]);
        return;
      }
      if (r.status === 500 || r.status === 502 || r.status === 504) {
        setMsgs((m) => [...m, { role: "assistant",
          content: "ระบบขัดข้องชั่วคราว ลองใหม่อีกครั้ง", isError: true, retryText: q }]);
        return;
      }
      if (!r.ok) {
        setMsgs((m) => [...m, { role: "assistant",
          content: "เกิดข้อผิดพลาด ลองใหม่อีกครั้ง", isError: true, retryText: q }]);
        return;
      }

      const d = await r.json();
      setSid(d.session_id);
      setMsgs((m) => [...m, { role: "assistant", content: d.answer, route: d.route,
                              sources: d.sources, latency_ms: d.latency_ms,
                              confidence: d.confidence, trace: d.trace, reasoning: d.reasoning,
                              message_id: d.message_id, rating: null }]);
      loadSessions(); // session ใหม่/หัวข้ออาจเปลี่ยน อัปเดต sidebar ให้ตรง
    } catch (err: any) {
      if (err?.name === "AbortError") {
        setMsgs((m) => [...m, { role: "assistant",
          content: "คำขอใช้เวลานานเกินไป ลองใหม่อีกครั้ง", isError: true, retryText: q }]);
      } else {
        setMsgs((m) => [...m, { role: "assistant",
          content: "ตอนนี้ระบบไม่พร้อมใช้งาน ตรวจสอบอินเทอร์เน็ตแล้วลองใหม่อีกครั้ง",
          isError: true, retryText: q }]);
      }
    } finally {
      clearTimeout(timer);
      setBusy(false);
    }
  }

  async function send() {
    const q = text.trim();
    if (!q || busy) return;
    setText("");
    setMsgs((m) => [...m, { role: "user", content: q }]);   // แสดงทันทีไม่ต้องรอ server
    await runQuery(q);
  }

  function retry(q: string) {
    if (busy) return;
    runQuery(q);
  }

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <aside style={{ width: 220, flexShrink: 0, borderRight: "1px solid #232838",
                      padding: 12, display: "flex", flexDirection: "column", gap: 8 }}>
        <button onClick={newChat}
                style={{ padding: "10px 12px", borderRadius: 10, border: "none",
                         background: "#e91e63", color: "#fff", cursor: "pointer", fontWeight: 600 }}>
          + แชทใหม่
        </button>
        <div style={{ flex: 1, overflowY: "auto", display: "grid", gap: 4, marginTop: 4 }}>
          {sessions.map((s) => (
            <button key={s.session_id} onClick={() => openSession(s.session_id)}
                    style={{ textAlign: "left", padding: "8px 10px", borderRadius: 8, border: "none",
                             cursor: "pointer", fontSize: 13, fontFamily: "inherit",
                             background: s.session_id === sid ? "#232838" : "transparent",
                             color: "#e6e6e6", overflow: "hidden", textOverflow: "ellipsis",
                             whiteSpace: "nowrap" }}>
              {s.title || "บทสนทนาไม่มีชื่อ"}
            </button>
          ))}
          {!sessions.length && (
            <div style={{ opacity: 0.4, fontSize: 12, padding: 8 }}>ยังไม่มีประวัติ</div>
          )}
        </div>
      </aside>

      <main style={{ flex: 1, maxWidth: 760, margin: "0 auto", padding: 16, minHeight: "100vh",
                     display: "flex", flexDirection: "column" }}>
        <h1 style={{ fontSize: 22 }}>ช่วยด้วย</h1>

        <div style={{ flex: 1, display: "grid", gap: 12, alignContent: "start" }}>
          {loadingHistory && <div style={{ opacity: 0.5 }}>กำลังโหลดประวัติ…</div>}
          {msgs.map((m, i) => (
            <div key={i} style={{ justifySelf: m.role === "user" ? "end" : "start", maxWidth: "85%" }}>
              <div style={{ padding: "10px 14px", borderRadius: 12,
                            background: m.role === "user" ? "#e91e63" : (m.isError ? "#2a151c" : "#161a22"),
                            border: m.isError ? "1px solid #7a2a3a" : undefined }}>
                {m.role === "user" ? (
                  <div style={{ whiteSpace: "pre-wrap" }}>{m.content}</div>
                ) : m.isError ? (
                  <div>{m.content}</div>
                ) : (
                  <div className="markdown">
                    <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>
                      {linkifyRefs(m.content, i)}
                    </ReactMarkdown>
                  </div>
                )}
              </div>

              {m.isError && m.retryText && (
                <button onClick={() => retry(m.retryText!)} disabled={busy}
                        style={{ marginTop: 4, padding: "4px 10px", borderRadius: 8,
                                 border: "1px solid #7a2a3a", background: "none", color: "#ff8fa3",
                                 cursor: busy ? "default" : "pointer", fontSize: 12 }}>
                  ลองใหม่
                </button>
              )}

              {m.role === "assistant" && m.route && (
                <button
                  onClick={() => m.trace && toggleTrace(i)}
                  style={{
                    fontSize: 12, opacity: 0.65, marginTop: 4, display: "flex", alignItems: "center",
                    gap: 6, background: "none", border: "none", color: "inherit", padding: 0,
                    cursor: m.trace ? "pointer" : "default", fontFamily: "inherit",
                  }}
                  title={m.trace ? "กดดูว่า agent ตัดสินใจยังไง" : undefined}
                >
                  <span>{ROUTE_LABEL[m.route] ?? m.route}</span>
                  {m.latency_ms != null && <span>· {m.latency_ms} ms</span>}
                  {m.confidence != null && (
                    <span>· ความมั่นใจในการเลือกเส้นทาง {(m.confidence * 100).toFixed(0)}%</span>
                  )}
                  {m.trace && <span>{openTrace.has(i) ? "▲" : "▼"}</span>}
                </button>
              )}

              {m.trace && openTrace.has(i) && (
                <div style={{ marginTop: 6, padding: "10px 12px", borderRadius: 10,
                              background: "#12151c", border: "1px solid #232838", fontSize: 12 }}>
                  {m.trace.decided_at_layer && (
                    <div style={{ opacity: 0.7, marginBottom: 8 }}>
                      ตัดสินใจที่ชั้น: {LAYER_LABEL[m.trace.decided_at_layer] ?? m.trace.decided_at_layer}
                    </div>
                  )}
                  {!!m.trace.steps?.length && (() => {
                    const total = m.trace.steps!.reduce((s, st) => s + st.ms, 0) || 1;
                    return (
                      <div style={{ display: "grid", gap: 6 }}>
                        {m.trace.steps!.map((st, si) => (
                          <div key={si}>
                            <div style={{ display: "flex", justifyContent: "space-between", opacity: 0.85 }}>
                              <span>{st.name}</span><span>{st.ms} ms</span>
                            </div>
                            <div style={{ background: "#1c212c", borderRadius: 4, height: 6, marginTop: 3 }}>
                              <div style={{ width: `${(st.ms / total) * 100}%`, background: "#e91e63",
                                            height: "100%", borderRadius: 4 }} />
                            </div>
                          </div>
                        ))}
                      </div>
                    );
                  })()}
                  {(m.reasoning || m.trace.reasoning) && (
                    <div style={{ marginTop: 8, opacity: 0.8, fontStyle: "italic" }}>
                      {m.reasoning ?? m.trace.reasoning}
                    </div>
                  )}
                </div>
              )}

              {/* 4 ใน 5 route คืน sources ว่าง — ต้องไม่โชว์หัวข้อเปล่า */}
              {!!m.sources?.length && (
                <ol style={{ fontSize: 13, opacity: 0.8, marginTop: 6 }}>
                  {m.sources.map((s: any) => (
                    <li key={s.ref} id={`src-${i}-${s.ref}`} style={{ scrollMarginTop: 80 }}>
                      {s.url ? <a href={s.url} style={{ color: "#7bb3ff" }}>{s.title}</a> : s.title}
                    </li>
                  ))}
                </ol>
              )}

              {m.role === "assistant" && m.message_id && (
                <div style={{ display: "flex", gap: 6, marginTop: 6 }}>
                  <button onClick={() => rate(i, 1)} title="คำตอบนี้มีประโยชน์"
                          style={{ ...voteBtn, opacity: m.rating === 1 ? 1 : 0.45 }}>👍</button>
                  <button onClick={() => rate(i, -1)} title="คำตอบนี้ไม่มีประโยชน์"
                          style={{ ...voteBtn, opacity: m.rating === -1 ? 1 : 0.45 }}>👎</button>
                </div>
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
    </div>
  );
}

const voteBtn = {
  padding: "4px 10px", borderRadius: 8, border: "1px solid #2a2f3a",
  background: "#161a22", cursor: "pointer", fontSize: 14,
};
