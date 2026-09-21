// endpoint ของหน้าเว็บเอง ใช้ให้ docker เช็กว่า container พร้อมหรือยัง
// ไม่ได้ส่งต่อไป api เพราะต้องการรู้ว่า "หน้าเว็บ" พร้อม ไม่ใช่ "หลังบ้าน" พร้อม
export const dynamic = "force-dynamic";
export function GET() {
  return Response.json({ status: "ok", service: "web", version: "0.1.0" });
}
