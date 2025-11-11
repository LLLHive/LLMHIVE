import AppShell from './components/AppShell';
import ChatSurface from './components/ChatSurface';
import LoginPage from './components/LoginPage';
import { auth } from '@/auth';

export default async function Page() {
  const session = await auth?.();
  if (!session?.user) {
    return <LoginPage />;
  }
  return (
    <AppShell title="Chat">
      <div className="mx-auto max-w-4xl">
        <ChatSurface />
      </div>
    </AppShell>
  );
}
