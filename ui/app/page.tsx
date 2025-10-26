import { auth, signIn, signOut } from "@/auth";
import Link from "next/link";
import PromptForm from "./components/PromptForm";
import styles from "./page.module.css";

function SignIn() {
  return (
    <form
      action={async () => {
        "use server";
        await signIn("github");
      }}
    >
      <button type="submit" className={styles.authButton}>Sign in with GitHub</button>
    </form>
  );
}

function SignOut({ user }: { user: any }) {
  return (
    <div className={styles.userInfo}>
      <span>Welcome, {user?.name}</span>
      <form
        action={async () => {
          "use server";
          await signOut();
        }}
      >
        <button type="submit" className={styles.authButton}>Sign Out</button>
      </form>
    </div>
  );
}

export default async function Home() {
  const session = await auth();

  return (
    <main className={styles.main}>
      <header className={styles.header}>
        <h1 className={styles.title}>LLMHive Orchestrator</h1>
        {session?.user ? <SignOut user={session.user} /> : <SignIn />}
      </header>

      <div className={styles.content}>
        {session?.user ? (
          <PromptForm />
        ) : (
          <p className={styles.signInMessage}>Please sign in to use the orchestrator.</p>
        )}
      </div>
    </main>
  );
}
