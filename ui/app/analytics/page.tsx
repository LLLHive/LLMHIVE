import AppShell from '../components/AppShell';
import LoginPage from '../components/LoginPage';
import { auth } from '@/auth';

export default async function AnalyticsPage() {
  const session = await auth?.();
  if (!session?.user) {
    return <LoginPage />;
  }
  return (
    <AppShell title="Analytics">
      <div className="mx-auto max-w-4xl text-text-dim py-10">
        <p>Analytics coming soon…</p>
      </div>
    </AppShell>
  );
}
