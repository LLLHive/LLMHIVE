import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LLMHive",
  description: "Multi-Agent LLM Orchestration Platform",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode; }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}