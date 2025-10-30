import { auth, signIn, signOut } from "@/auth";
import type { User } from "next-auth";
import PromptForm from "./components/PromptForm";
import Sidebar from "./components/Sidebar";
import styles from "./page.module.css";
import { Suspense } from "react";

function SignIn() {
  return (
    <form
      action={async () => {
        "use server";
        await signIn("github");
      }}
    >
      <button type="submit" className={styles.authButton}>
        Sign in with GitHub
      </button>
    </form>
  );
}

function SignOut({ user }: { user: User }) {
  return (
    <div className={styles.userInfo}>
      <span className={styles.userGreeting}>Signed in as {user?.name || "Innovator"}</span>
      <form
        action={async () => {
          "use server";
          await signOut();
        }}
      >
        <button type="submit" className={styles.authButton}>Sign out</button>
      </form>
    </div>
  );
}

export default async function Home() {
  try {
    const session = await auth();
    const user = session?.user ?? null;

    return (
      <main className={styles.shell}>
        <Sidebar displayName={user?.name ?? user?.email ?? null} />
        <div className={styles.canvas}>
          <header className={styles.hero}>
            <div className={styles.heroCopy}>
              <div className={styles.breadcrumb}>Dashboard • Compose</div>
              <h1 className={styles.title}>LLMHive Orchestration Studio</h1>
              <p className={styles.subtitle}>
                Shape your collective of models, reasoning modes, and workflows in an interface inspired by the flagship LLM chat experiences.
              </p>
            </div>
            <div>{user ? <SignOut user={user} /> : <SignIn />}</div>
          </header>

          <nav className={styles.menuRow} aria-label="Primary">
            <button className={`${styles.menuButton} ${styles.menuButtonActive}`} type="button">
              Compose
            </button>
            <button className={styles.menuButton} type="button">
              Evaluations
            </button>
            <button className={styles.menuButton} type="button">
              Activity
            </button>
            <button className={styles.menuButton} type="button">
              Playground
            </button>
          </nav>

          <div className={styles.content}>
            {user ? (
              <Suspense fallback={<div className={styles.loading}>Loading orchestration cockpit…</div>}>
                <PromptForm userId={user.email ?? user.id ?? "guest"} />
              </Suspense>
            ) : (
              <div className={styles.welcomePanel}>
                <h2>Summon the hive</h2>
                <p>
                  Sign in to choose your ensemble of LLMs, activate advanced reasoning strategies, and orchestrate responses that feel as fluid as a frontier chat experience.
                </p>
              </div>
            )}
          </div>
        </div>
      </main>
    );
  } catch (error) {
    console.error("Home page error:", error);
    return (
      <main className={styles.shell}>
        <Sidebar displayName={null} />
        <div className={styles.canvas}>
          <header className={styles.hero}>
            <div className={styles.heroCopy}>
              <div className={styles.breadcrumb}>Dashboard • Compose</div>
              <h1 className={styles.title}>LLMHive Orchestration Studio</h1>
              <p className={styles.subtitle}>Experience next-generation collaborative intelligence.</p>
            </div>
          </header>
          <div className={styles.content}>
            <p className={styles.error}>An error occurred while loading the page. Please try again later.</p>
          </div>
        </div>
      </main>
    );
  }
}
