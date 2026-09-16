import type { Metadata } from "next";
import "./globals.css";
import "./ui-overrides.css";

export const metadata: Metadata = {
  title: "AgriSaathi — Smart Farming",
  description: "A calm, intelligent precision-agriculture dashboard for farmers.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
