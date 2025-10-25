import type { Metadata } from "next";
import { auth } from "@/auth";
import { SessionProvider } from "next-auth/react";
import "./globals.css";

export const metadata: Metadata = {
  title: "LLMHive",
  description: "Multi-Agent LLM Orchestration Platform",
};

export default async function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode; }>) {
  const session = await auth();
  
  return (
    <html lang="en">
      <body>
        <SessionProvider session={session}>{children}</SessionProvider>
      </body>
    </html>
  );
}