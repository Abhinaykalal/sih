import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
    title: "AgriSaathi AI — Mobile Platform & Core API",
    description: "Intelligent Agricultural IoT & Precision Decision Platform for Mobile.",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en">
            <body style={{ margin: 0, fontFamily: "system-ui, sans-serif", backgroundColor: "#F5FBF1", color: "#123D25" }}>
                {children}
            </body>
        </html>
    );
}
