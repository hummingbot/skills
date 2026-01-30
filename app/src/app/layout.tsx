import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Image from "next/image";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Hummingbot Skills",
  description: "AI agent skills for Hummingbot algorithmic trading infrastructure",
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-black text-white min-h-screen`}
      >
        <header className="border-b border-white/10">
          <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
            <a href="/" className="flex items-center gap-2 text-white hover:text-white/80">
              <Image src="/logo.png" alt="Hummingbot" width={28} height={28} />
              <span className="font-mono text-lg tracking-wide">Hummingbot Skills</span>
            </a>
            <nav className="flex items-center gap-6">
              <a href="https://github.com/hummingbot/skills" target="_blank" rel="noopener noreferrer" className="text-sm text-white/60 hover:text-white">
                GitHub
              </a>
              <a href="https://hummingbot.org" target="_blank" rel="noopener noreferrer" className="text-sm text-white/60 hover:text-white">
                Hummingbot
              </a>
            </nav>
          </div>
        </header>
        {children}
      </body>
    </html>
  );
}
