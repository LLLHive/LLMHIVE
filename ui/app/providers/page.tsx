import AppShell from '../components/AppShell';
import LoginPage from '../components/LoginPage';
import { auth } from '@/auth';

export default async function ProvidersPage() {
  const session = await auth?.();
  if (!session?.user) {
    return <LoginPage />;
  }
  return (
    <AppShell title="Providers">
      <div className="mx-auto max-w-4xl text-text-dim py-10">
        <p>Providers coming soon…</p>
      </div>
    </AppShell>
  );
}
