"use client";
import { useEffect, useRef, useState } from "react";
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

// คำถามตัวอย่างในคอลัมน์ขวา กดแล้วส่งได้เลย
// เลี่ยงคำถามชุดเดียวกับ scripts/smoke_test.sh เพื่อไม่ให้รายการแชทซ้ำกันเวลาสาธิต
const SAMPLES = [
  "เครื่องร้อนมากตอนชาร์จ ปกติไหม",
  "ลืมรหัสผ่านอีเมล ทำยังไงดี",
  "อัปเดตแล้วแอปเด้งตลอด แก้ยังไง",
  "พื้นที่มือถือเต็ม ลบอะไรได้บ้าง",
];

// ไอคอนเส้นบาง วาดเองด้วย SVG — อีโมจิจะถูกเรนเดอร์เป็นภาพสีบนมือถือ ทำให้หน้าตาไม่ตรงกับบนคอม
const IconMenu = () => (
  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
    <path d="M4 7h16M4 12h16M4 17h16" />
  </svg>
);
const IconChat = () => (
  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 12a7 7 0 0 1-7 7H8l-4 3v-4.3A7 7 0 0 1 4 12a7 7 0 0 1 7-7h2a7 7 0 0 1 7 7Z" />
  </svg>
);
const IconPlus = () => (
  <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <path d="M12 5v14M5 12h14" />
  </svg>
);
const IconSend = () => (
  <svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M5 12h13M12 5l7 7-7 7" />
  </svg>
);
const IconCopy = () => (
  <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.6"
       strokeLinecap="round" strokeLinejoin="round">
    <rect x="9" y="9" width="11" height="11" rx="2.5" />
    <path d="M15 5.5A2.5 2.5 0 0 0 12.5 3h-6A3.5 3.5 0 0 0 3 6.5v6A2.5 2.5 0 0 0 5.5 15" />
  </svg>
);
const IconUp = () => (
  <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.6"
       strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3Z" />
    <path d="M7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3" />
  </svg>
);
const IconDown = () => (
  <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.6"
       strokeLinecap="round" strokeLinejoin="round">
    <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3Z" />
    <path d="M17 2h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17" />
  </svg>
);
const IconLogout = () => (
  <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 7V5a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2v-2M10 12h10m0 0-3-3m3 3-3 3" />
  </svg>
);

const CHAT_TIMEOUT_MS = 90_000; // web→api เพดาน 90 วินาทีตาม CONTRACT §0

type TraceStep = { name: string; ms: number };
type Trace = { decided_at_layer?: string; steps?: TraceStep[]; reasoning?: string };
type Msg = { role: "user" | "assistant"; content: string; route?: string; created_at?: string;
             sources?: any[]; latency_ms?: number; confidence?: number;
             trace?: Trace; reasoning?: string; message_id?: string;
             rating?: 1 | -1 | null; isError?: boolean; retryText?: string };
type SessionSummary = { session_id: string; title?: string; updated_at?: string };

// แทนที่ [1] [2] ในคำตอบด้วยลิงก์ที่เลื่อนไปหา source ตัวนั้น
// ผูกกับ msgIndex เพื่อไม่ให้ id ชนกันข้ามข้อความ
function linkifyRefs(text: string, msgIndex: number) {
  return text.replace(/\[(\d+)\]/g, (_m, n) => `[[${n}]](#src-${msgIndex}-${n})`);
}

// เวลาแบบ 24 ชั่วโมงตามเครื่องผู้ใช้ เช่น 10:24
function labelSources(sources: any[]) {
  // เอกสารยาวถูกตัดเป็นหลาย chunk ทุก chunk จึงมี title เดียวกัน
  // ถ้าปล่อยไว้หน้าเว็บจะดูเหมือนระบบอ้างเอกสารเดิมซ้ำ ๆ เลยเติมเลขตอนเฉพาะชื่อที่ซ้ำ
  const total = new Map<string, number>();
  for (const s of sources) total.set(s.title, (total.get(s.title) ?? 0) + 1);
  const seen = new Map<string, number>();
  return sources.map((s) => {
    if ((total.get(s.title) ?? 0) < 2) return { ...s, label: s.title };
    const n = (seen.get(s.title) ?? 0) + 1;
    seen.set(s.title, n);
    return { ...s, label: `${s.title} (ตอนที่ ${n})` };
  });
}

function timeText(iso?: string) {
  if (!iso) return "";
  const d = new Date(iso);
  return isNaN(d.getTime()) ? "" : d.toLocaleTimeString("th-TH", { hour: "2-digit", minute: "2-digit" });
}

export default function Chat() {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [sid, setSid] = useState<string | null>(null);
  const [openTrace, setOpenTrace] = useState<Set<number>>(new Set());
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [userName, setUserName] = useState("");
  const [sideOpen, setSideOpen] = useState(true);
  const [stats, setStats] = useState<any>(null);
  const [copied, setCopied] = useState<number | null>(null);
  const [rated, setRated] = useState<Record<number, 1 | -1>>({});
  const threadRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch("/api/auth/me")
      .then(async (r) => {
        if (r.status === 401) { location.href = "/login"; return; }
        const d = await r.json();
        setUserName(d?.user?.name || d?.user?.username || d?.user?.id || "บัญชีของฉัน");
      })
      .catch(() => {
        // เรียก /me ไม่ได้ ไม่ต้องเด้งออก ปล่อยให้ลองใช้งานต่อ
      });
    loadSessions();
    loadStats();
    // จอเล็กเริ่มต้นเป็นปิด ส่วนจอใหญ่จำค่าที่ผู้ใช้เลือกไว้ครั้งก่อน
    const narrow = window.matchMedia("(max-width: 780px)").matches;
    const saved = localStorage.getItem("sideOpen");
    setSideOpen(narrow ? false : saved !== "0");
  }, []);

  function toggleSide() {
    setSideOpen((open) => {
      localStorage.setItem("sideOpen", open ? "0" : "1");
      return !open;
    });
  }

  // ข้อความใหม่มาแล้วเลื่อนลงล่างสุดให้เอง
  useEffect(() => {
    const el = threadRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [msgs, busy]);

  async function loadSessions() {
    try {
      const r = await fetch("/api/sessions");
      if (!r.ok) return;
      const d = await r.json();
      // ถามคำเดิมซ้ำหลายรอบ (เช่นตอนรันชุดทดสอบ) จะได้แชทชื่อเดียวกันเต็มแถบ
      // โชว์เฉพาะอันล่าสุดของแต่ละหัวข้อ ของเก่ายังอยู่ในฐานข้อมูลเหมือนเดิม
      const seen = new Set<string>();
      const unique = (d.sessions ?? []).filter((s: SessionSummary) => {
        const key = (s.title || "").trim();
        if (!key) return true;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      });
      setSessions(unique);
    } catch {
      // โหลดรายการ session ไม่สำเร็จ ไม่ต้องเด้ง error แค่ sidebar จะว่างไปก่อน
    }
  }

  // จอเล็กเปิดแถบซ้ายทับหน้าจออยู่ เลือกอะไรแล้วต้องปิดให้เอง ไม่งั้นค้างบังแชท
  function closeSideOnNarrow() {
    if (window.matchMedia("(max-width: 780px)").matches) setSideOpen(false);
  }

  async function loadStats() {
    try {
      const r = await fetch("/api/stats");
      if (r.ok) setStats(await r.json());
    } catch {
      // ดึงสถิติไม่ได้ก็แค่ไม่โชว์การ์ด ไม่ต้องรบกวนผู้ใช้
    }
  }

  async function sendFeedback(i: number, messageId: string, rating: 1 | -1) {
    if (rated[i]) return;                       // กดได้ครั้งเดียวต่อคำตอบ
    setRated((r) => ({ ...r, [i]: rating }));   // ขึ้นให้เห็นทันที ไม่ต้องรอเซิร์ฟเวอร์
    try {
      const res = await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message_id: messageId, rating }),
      });
      if (!res.ok) throw new Error(String(res.status));
    } catch {
      // ส่งไม่สำเร็จ ให้ปุ่มกลับมากดได้ใหม่ ไม่ต้องขึ้น error รบกวนกลางบทสนทนา
      setRated((r) => {
        const next = { ...r };
        delete next[i];
        return next;
      });
    }
  }

  async function copyAnswer(i: number, textToCopy: string) {
    try {
      await navigator.clipboard.writeText(textToCopy);
      setCopied(i);
      setTimeout(() => setCopied((cur) => (cur === i ? null : cur)), 1600);
    } catch {
      // เบราว์เซอร์ไม่อนุญาตให้คัดลอก (เช่นเปิดผ่าน http บนมือถือบางรุ่น)
    }
  }

  function newChat() {
    setSid(null);
    setMsgs([]);
    setOpenTrace(new Set());
    closeSideOnNarrow();
  }

  // session ที่ยังไม่มีข้อความ (พึ่งสร้าง) จะได้ messages: [] แบบ 200 ปกติ ไม่ใช่ error (CONTRACT §6 ข้อ 3)
  async function openSession(id: string) {
    setLoadingHistory(true);
    setOpenTrace(new Set());
    closeSideOnNarrow();
    try {
      const r = await fetch(`/api/history/${id}`);
      if (r.status === 401) { location.href = "/login"; return; }
      const d = await r.json();
      setSid(d.session_id ?? id);
      const loaded: Msg[] = (d.messages ?? []).map((mm: any) => ({
        role: mm.role, content: mm.content, route: mm.route, sources: mm.sources,
        message_id: mm.message_id, rating: mm.rating ?? null, created_at: mm.created_at,
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

  async function logout() {
    try {
      await fetch("/api/auth/logout", { method: "POST" });
    } catch {
      // ออกจากระบบฝั่ง server ไม่สำเร็จก็ยังพากลับไปหน้าเข้าสู่ระบบ
    }
    location.href = "/login";
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
                              message_id: d.message_id, rating: null,
                              created_at: d.created_at ?? new Date().toISOString() }]);
      loadSessions();
      loadStats();     // ตัวเลขในการ์ดสถิติจะได้ขยับตามการใช้งานจริง // session ใหม่/หัวข้ออาจเปลี่ยน อัปเดต sidebar ให้ตรง
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
    setMsgs((m) => [...m, { role: "user", content: q, created_at: new Date().toISOString() }]);   // แสดงทันทีไม่ต้องรอ server
    await runQuery(q);
  }

  function ask(q: string) {
    if (busy) return;
    setMsgs((m) => [...m, { role: "user", content: q, created_at: new Date().toISOString() }]);
    runQuery(q);
  }

  function retry(q: string) {
    if (busy) return;
    runQuery(q);
  }

  const headTitle = msgs.find((m) => m.role === "user")?.content
    || sessions.find((s) => s.session_id === sid)?.title
    || "แชทช่วยแก้ปัญหา";

  return (
    <div className={`app${sideOpen ? "" : " side-closed"}`}>
      {/* ฉากหลังของ drawer บนจอเล็ก กดแล้วปิดแถบซ้าย */}
      <div className="scrim" onClick={() => setSideOpen(false)} />

      <aside className="sidebar">
        <div className="brand">
          <img src="/img/logo.png" alt="" />
          <div>
            <div className="brand-name">ช่วยด้วย</div>
            <div className="brand-sub">ChuayDuay</div>
          </div>
        </div>

        <button className="btn-new" onClick={newChat}><IconPlus /> เริ่มแชทใหม่</button>

        <div className="side-label">แชทล่าสุด</div>
        <div className="session-list">
          {sessions.map((s) => (
            <button key={s.session_id}
                    className={`session${s.session_id === sid ? " active" : ""}`}
                    onClick={() => openSession(s.session_id)}>
              <IconChat /> <span className="session-title">{s.title || "บทสนทนาไม่มีชื่อ"}</span>
            </button>
          ))}
          {!sessions.length && <div className="side-label">ยังไม่มีประวัติ</div>}
        </div>

        <div className="side-bottom">
          <div className="side-foot">Better Tech Together</div>
          <button className="account" onClick={logout} title="ออกจากระบบ">
            <img src="/img/avatar.png" alt="" />
            <span className="account-name">{userName || "บัญชีของฉัน"}</span>
            <IconLogout />
          </button>
        </div>
      </aside>

      <main className="main">
        {/* ใบไม้จาง ๆ สองมุมล่าง ให้ได้ฟีลแต่ไม่ดึงสายตา จางลงอีกเมื่อเริ่มคุย */}
        <img className={`main-foliage${msgs.length ? " dim" : ""}`} src="/img/foliage.png" alt="" />
        <img className={`main-foliage right${msgs.length ? " dim" : ""}`} src="/img/foliage.png" alt="" />

        <div className="main-head">
          <button className="btn-side" onClick={toggleSide}
                  title={sideOpen ? "ซ่อนแถบด้านข้าง" : "แสดงแถบด้านข้าง"}
                  aria-label="เปิดปิดแถบด้านข้าง"><IconMenu /></button>
          <div style={{ minWidth: 0 }}>
            <h1 className="main-title">{headTitle}</h1>
            <p className="main-sub">ค่อย ๆ แก้ไปด้วยกัน ทีละขั้นตอน</p>
          </div>
          <div className="status"><span className="dot" /> พร้อมช่วยคุณ</div>
        </div>

        <div className="thread" ref={threadRef}>
          {loadingHistory && <div className="side-label">กำลังโหลดประวัติ…</div>}

          {!msgs.length && !loadingHistory && (
            <div className="empty">
              <img src="/img/mascot.png" alt="" />
              <div style={{ fontSize: 20, fontWeight: 700, color: "var(--text)" }}>
                สวัสดีครับ มีปัญหาไอทีอะไรให้ช่วยไหม
              </div>
              <div>พิมพ์คำถามด้านล่าง หรือเลือกคำถามที่พบบ่อยทางขวาได้เลย</div>
            </div>
          )}

          {msgs.map((m, i) => (
            <div key={i} className={`row ${m.role === "user" ? "user" : "bot"}`}>
              {m.role === "assistant" && (
                <div className="avatar"><img src="/img/avatar.png" alt="" /></div>
              )}

              <div className="bubble-wrap">
                {m.role === "assistant" && !m.isError && (
                  <div className="who">ช่วยด้วย <span className="time">{timeText(m.created_at)}</span></div>
                )}

                <div className={`bubble${m.isError ? " error" : ""}`}>
                  {m.role === "user" || m.isError ? (
                    m.content
                  ) : (
                    <div className="markdown">
                      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>
                        {linkifyRefs(m.content, i)}
                      </ReactMarkdown>
                    </div>
                  )}
                </div>

                {m.role === "user" && m.created_at && (
                  <div className="time user-time">{timeText(m.created_at)}</div>
                )}

                {m.role === "assistant" && !m.isError && (
                  <div className="msg-actions">
                    <button className="copy" onClick={() => copyAnswer(i, m.content)}
                            title="คัดลอกคำตอบ">
                      <IconCopy /> {copied === i ? "คัดลอกแล้ว" : "คัดลอก"}
                    </button>
                    {m.message_id && (
                      <>
                        <button className={`copy rate${rated[i] === 1 ? " on" : ""}`}
                                onClick={() => sendFeedback(i, m.message_id!, 1)}
                                disabled={!!rated[i]}
                                aria-label="คำตอบนี้ช่วยได้"
                                title={rated[i] ? "ขอบคุณสำหรับคะแนน" : "คำตอบนี้ช่วยได้"}>
                          <IconUp />
                        </button>
                        <button className={`copy rate${rated[i] === -1 ? " on" : ""}`}
                                onClick={() => sendFeedback(i, m.message_id!, -1)}
                                disabled={!!rated[i]}
                                aria-label="คำตอบนี้ยังไม่ช่วย"
                                title={rated[i] ? "ขอบคุณสำหรับคะแนน" : "คำตอบนี้ยังไม่ช่วย"}>
                          <IconDown />
                        </button>
                      </>
                    )}
                  </div>
                )}

                {m.isError && m.retryText && (
                  <button className="btn-retry" onClick={() => retry(m.retryText!)} disabled={busy}>
                    ลองใหม่
                  </button>
                )}

                {m.role === "assistant" && m.route && (
                  <button className="meta" onClick={() => m.trace && toggleTrace(i)}
                          style={{ cursor: m.trace ? "pointer" : "default" }}
                          title={m.trace ? "กดดูว่า agent ตัดสินใจยังไง" : undefined}>
                    <span className="tag">{ROUTE_LABEL[m.route] ?? m.route}</span>
                    {m.latency_ms != null && <span>{m.latency_ms} ms</span>}
                    {m.confidence != null && (
                      <span>· ความมั่นใจในการเลือกเส้นทาง {(m.confidence * 100).toFixed(0)}%</span>
                    )}
                    {m.trace && <span>{openTrace.has(i) ? "▲" : "▼"}</span>}
                  </button>
                )}

                {m.trace && openTrace.has(i) && (
                  <div className="trace">
                    {m.trace.decided_at_layer && (
                      <div style={{ marginBottom: 10, color: "var(--primary)", fontWeight: 600 }}>
                        ตัดสินใจที่ชั้น: {LAYER_LABEL[m.trace.decided_at_layer] ?? m.trace.decided_at_layer}
                      </div>
                    )}
                    {!!m.trace.steps?.length && (() => {
                      const total = m.trace.steps!.reduce((s, st) => s + st.ms, 0) || 1;
                      return (
                        <div style={{ display: "grid", gap: 8 }}>
                          {m.trace.steps!.map((st, si) => (
                            <div key={si}>
                              <div style={{ display: "flex", justifyContent: "space-between" }}>
                                <span>{st.name}</span><span>{st.ms} ms</span>
                              </div>
                              <div className="trace-bar">
                                <i style={{ width: `${(st.ms / total) * 100}%` }} />
                              </div>
                            </div>
                          ))}
                        </div>
                      );
                    })()}
                    {(m.reasoning || m.trace.reasoning) && (
                      <div style={{ marginTop: 10, fontStyle: "italic" }}>
                        {m.reasoning ?? m.trace.reasoning}
                      </div>
                    )}
                  </div>
                )}

                {/* 4 ใน 5 route คืน sources ว่าง — ต้องไม่โชว์หัวข้อเปล่า */}
                {!!m.sources?.length && (
                  <ol className="sources">
                    {labelSources(m.sources).map((s: any) => (
                      <li key={s.ref} id={`src-${i}-${s.ref}`} style={{ scrollMarginTop: 80 }}>
                        {/* ที่มาของเอกสารเป็นที่อยู่ภายในระบบ กดไปไหนไม่ได้ จึงแสดงเป็นข้อความเฉย ๆ */}
                        {s.label}
                      </li>
                    ))}
                  </ol>
                )}

              </div>
            </div>
          ))}

          {busy && (
            <div className="row bot">
              <div className="avatar"><img src="/img/avatar.png" alt="" /></div>
              <div className="bubble-wrap">
                <div className="bubble">
                  <span className="thinking"><i /><i /><i /> กำลังคิด…</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {!msgs.length && (
          <div className="samples-narrow">
            {SAMPLES.map((q) => (
              <button key={q} className="chip-narrow" onClick={() => ask(q)} disabled={busy}>{q}</button>
            ))}
          </div>
        )}

        <div className="composer">
          <input value={text} onChange={(e) => setText(e.target.value)}
                 onKeyDown={(e) => e.key === "Enter" && send()}
                 placeholder="พิมพ์ปัญหาไอทีของคุณได้เลย…" />
          <button className="btn-send" onClick={send} disabled={busy} title="ส่ง" aria-label="ส่ง"><IconSend /></button>
        </div>
      </main>

      <aside className="panel">
        <div className="card">
          <h2>คำถามที่พบบ่อย</h2>
          {SAMPLES.map((q) => (
            <button key={q} className="chip" onClick={() => ask(q)} disabled={busy}>{q}</button>
          ))}
        </div>

        {stats && (
          <div className="card">
            <h2>สถิติระบบ</h2>
            <div className="stat-row"><span>คำถามทั้งหมด</span><b>{stats.total_requests}</b></div>
            <div className="stat-row"><span>เวลาตอบเฉลี่ย</span><b>{(stats.avg_latency_ms / 1000).toFixed(1)} วิ</b></div>
            <div className="stat-row"><span>ช้าสุด 5% แรก</span><b>{(stats.p95_latency_ms / 1000).toFixed(1)} วิ</b></div>
            {!!stats.total_requests && (
              <div className="routes">
                {Object.entries(stats.by_route as Record<string, number>)
                  .sort((a, b) => b[1] - a[1])
                  .map(([route, n]) => (
                    <div key={route} className="route-row">
                      <span>{ROUTE_LABEL[route] ?? route}</span>
                      <div className="route-bar">
                        <i style={{ width: `${(n / stats.total_requests) * 100}%` }} />
                      </div>
                      <b>{Math.round((n / stats.total_requests) * 100)}%</b>
                    </div>
                  ))}
              </div>
            )}
          </div>
        )}

        <div className="promo">
          <div>
            <h3>มีเพื่อน<span className="accent">ช่วยแล้ว</span></h3>
            <p>เรื่องไอที ค่อย ๆ แก้ไปด้วยกัน</p>
          </div>
          <img src="/img/mascot.png" alt="" />
        </div>
      </aside>
    </div>
  );
}
