import AppShell from './components/AppShell';
import ChatSurface from './components/ChatSurface';

export default function Page() {
  return (
    <AppShell title="Chat">
      <div className="mx-auto max-w-4xl">
        <ChatSurface />
      </div>
    </AppShell>
  );
}
