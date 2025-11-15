'use client';

import { signIn } from "next-auth/react";

export default function LoginPage() {
  return (
    <div className="min-h-[60vh] grid place-items-center">
      <div className="rounded-xl border border-border bg-panel p-8 text-center max-w-sm w-full">
        <h1 className="text-xl font-semibold">Sign in</h1>
        <p className="mt-2 text-text-dim text-sm">You need to sign in to continue.</p>
        <button
          type="button"
          onClick={() => signIn("github")}
          className="mt-4 inline-flex justify-center rounded-lg bg-gold text-bg px-4 py-2"
        >
          Sign in with GitHub
        </button>
      </div>
    </div>
  );
}
