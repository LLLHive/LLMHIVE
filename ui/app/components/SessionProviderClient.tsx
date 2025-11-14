"use client";

import { SessionProvider } from "next-auth/react";
import type { Session } from "next-auth";
import React from "react";

interface SessionProviderClientProps {
  children: React.ReactNode;
  session: Session | null;
}

/**
 * Client-side wrapper for SessionProvider.
 * 
 * This component must be a client component because NextAuth's SessionProvider
 * requires client-side context. By moving it to a separate client component,
 * we properly separate server and client boundaries in the Next.js app.
 */
export default function SessionProviderClient({
  children,
  session,
}: SessionProviderClientProps) {
  return (
    <SessionProvider session={session}>
      {children}
    </SessionProvider>
  );
}
