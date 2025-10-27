'use client';

import Image from "next/image";
import { signOut } from "next-auth/react";

interface SidebarProps {
  user: {
    name?: string | null;
    email?: string | null;
    image?: string | null;
  };
  onNewChat: () => void;
}

export default function Sidebar({ user, onNewChat }: SidebarProps) {
  return (
    <div className="w-64 bg-gray-950 border-r border-gray-800 flex flex-col h-full">
      {/* New Chat Button */}
      <div className="p-4">
        <button
          onClick={onNewChat}
          className="w-full py-3 px-4 bg-gray-800 hover:bg-gray-700 text-white rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
          aria-label="Start a new chat"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4v16m8-8H4"
            />
          </svg>
          New Chat
        </button>
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* User Profile Section */}
      <div className="p-4 border-t border-gray-800">
        <div className="flex items-center gap-3 mb-3">
          {user?.image ? (
            <Image
              src={user.image}
              alt={user.name || "User avatar"}
              width={40}
              height={40}
              className="rounded-full"
            />
          ) : (
            <div className="w-10 h-10 rounded-full bg-gray-700 flex items-center justify-center">
              <span className="text-lg font-semibold text-gray-300">
                {user?.name?.charAt(0).toUpperCase() || "U"}
              </span>
            </div>
          )}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">
              {user?.name || "User"}
            </p>
            <p className="text-xs text-gray-400 truncate">
              {user?.email || "No email"}
            </p>
          </div>
        </div>
        <button
          onClick={() => signOut()}
          className="w-full py-2 px-4 bg-gray-800 hover:bg-gray-700 text-white rounded-lg text-sm font-medium transition-colors"
          aria-label="Sign out from your account"
        >
          Sign Out
        </button>
      </div>
    </div>
  );
}
