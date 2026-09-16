import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'AgriSaathi AI — Precision Agriculture & Edge Advisory Platform',
  description: 'AI-driven crop diagnosis, smart crop recommendations, and real-time IoT field telemetry for precision farming.',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased bg-[#0A0F0D] text-gray-100 min-h-screen">
        {children}
      </body>
    </html>
  );
}
