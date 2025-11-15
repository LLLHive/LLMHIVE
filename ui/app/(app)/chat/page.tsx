'use client';

import ChatSurface from "../../components/ChatSurface";

export default function ChatPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Chat</h1>
      <div className="rounded-xl border border-border bg-panel p-4">
        <ChatSurface />
      </div>
    </div>
  );
}
