import dynamic from "next/dynamic";
const ChatSurface = dynamic(() => import("../../components/ChatSurface"), { ssr: false });

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
