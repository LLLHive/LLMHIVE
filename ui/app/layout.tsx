import type { Metadata } from "next";
import { auth } from "@/auth";
import "./globals.css";
import SessionProviderClient from "./components/SessionProviderClient";

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
        <SessionProviderClient session={session}>
          {children}
        </SessionProviderClient>
      </body>
    </html>
  );
}