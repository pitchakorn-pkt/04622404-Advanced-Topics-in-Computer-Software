// standalone: build ออกมาเป็นโฟลเดอร์เล็กที่มีแค่ของที่ใช้จริง image จะเล็กลงหลายเท่า
// rewrites: เบราว์เซอร์ยิง /api/... มาที่ Next.js แล้ว Next.js ฝั่ง server ส่งต่อไป http://api:8000
//   ทำแบบนี้เพราะเบราว์เซอร์ไม่รู้จักชื่อ "api" ใน docker network และไม่ต้องแก้ปัญหา CORS
//   ห้ามเอา URL ภายในไปใส่ NEXT_PUBLIC_* เพราะค่านั้นถูกฝังลงไฟล์ตอน build และหลุดถึงเบราว์เซอร์
const apiUrl = process.env.API_URL || "http://api:8000";

export default {
  output: "standalone",
  async rewrites() {
    return [{ source: "/api/:path((?!health).*)", destination: `${apiUrl}/api/:path*` }];
  },
};
