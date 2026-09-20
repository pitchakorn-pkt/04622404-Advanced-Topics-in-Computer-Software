import "./globals.css";

export const metadata = { title: "ช่วยด้วย (ChuayDuay)", description: "ผู้ช่วยแก้ปัญหามือถือและคอมพิวเตอร์" };

// interactiveWidget: ให้คีย์บอร์ดที่เด้งขึ้นมาย่อพื้นที่หน้าจอแทนที่จะทับช่องพิมพ์
// จำเป็นกับ Android (Chrome/Samsung) ที่หน้าจอถูกตรึงไว้ ส่วน iOS จะข้ามค่านี้ไปเอง
export const viewport = {
  width: "device-width",
  initialScale: 1,
  interactiveWidget: "resizes-content" as const,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    // lang="th" สำคัญกับการตัดบรรทัดภาษาไทยของเบราว์เซอร์
    <html lang="th">
      <head>
        {/* ฟอนต์ไทยจาก Google Fonts — ถ้าโหลดไม่ได้จะตกไปใช้ฟอนต์ระบบตามที่ตั้งไว้ใน globals.css */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Noto+Sans+Thai:wght@400;600;700;800&display=swap"
          rel="stylesheet"
        />
        <link rel="icon" href="/img/avatar.png" />
      </head>
      <body>{children}</body>
    </html>
  );
}
