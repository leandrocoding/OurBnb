import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Link from 'next/link';
import { Globe } from 'lucide-react';

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "OurBnb",
  description: "Plan your next group trip with ease",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased h-screen flex flex-col overflow-hidden`}
      >
        <header className="h-16 bg-white border-b border-slate-100 flex items-center px-6 z-50 flex-shrink-0">
          <Link href="/" className="flex items-center gap-2 text-rose-500 hover:text-rose-600 transition-colors">
            <Globe className="w-6 h-6" />
            <span className="font-bold text-xl tracking-tight text-slate-900">OurBnb</span>
          </Link>
        </header>
        <div className="flex-1 overflow-hidden relative">
          {children}
        </div>
      </body>
    </html>
  );
}
