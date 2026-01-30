import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
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
              <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" fill="none"/>
              </svg>
              <span className="font-mono text-sm tracking-wide">Skills</span>
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
