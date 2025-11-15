'use client';

import { signIn } from "next-auth/react";

export default function LoginPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-b from-gray-950 to-gray-900">
      <div className="w-full max-w-md p-8">
        {/* Logo/Title */}
        <div className="text-center mb-8">
          <h1 className="text-5xl font-bold text-white mb-3">LLMHive</h1>
          <p className="text-gray-400 text-lg">
            Multi-Agent LLM Orchestration Platform
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-gray-900 rounded-2xl shadow-2xl p-8 border border-gray-800">
          <h2 className="text-2xl font-semibold text-white mb-6 text-center">
            Welcome
          </h2>
          <p className="text-gray-400 text-center mb-8">
            Sign in to start orchestrating your AI agents
          </p>

          {/* GitHub Sign In Button */}
          <button
            onClick={() => signIn("github", { callbackUrl: "/" })}
            className="w-full py-3 px-4 bg-white hover:bg-gray-100 text-gray-900 rounded-lg font-semibold transition-colors flex items-center justify-center gap-3 shadow-lg"
          >
            <svg
              className="w-6 h-6"
              fill="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                fillRule="evenodd"
                d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
                clipRule="evenodd"
              />
            </svg>
            Sign in with GitHub
          </button>

          <p className="text-gray-500 text-xs text-center mt-6">
            By signing in, you agree to our Terms of Service and Privacy Policy
          </p>
        </div>
      </div>
    </div>
  );
}
