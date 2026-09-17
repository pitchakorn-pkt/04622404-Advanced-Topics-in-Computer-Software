import "./globals.css";

export const metadata = { title: "ช่วยด้วย", description: "ผู้ช่วยแก้ปัญหามือถือและคอมพิวเตอร์" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    // lang="th" สำคัญกับการตัดบรรทัดภาษาไทยของเบราว์เซอร์
    <html lang="th">
      <body style={{ fontFamily: "'Noto Sans Thai','IBM Plex Sans Thai',system-ui,sans-serif",
                     margin: 0, background: "#0f1115", color: "#e6e6e6" }}>
        {children}
      </body>
    </html>
  );
}
