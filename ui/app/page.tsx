import { auth, signIn, signOut } from "@/auth";
import type { User } from "next-auth";
import PromptForm from "./components/PromptForm";
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
      <span className={styles.userGreeting}>Welcome, {user?.name || "Innovator"}</span>
      <form
        action={async () => {
          "use server";
          await signOut();
        }}
      >
        <button type="submit" className={styles.authButton}>
          Sign Out
        </button>
      </form>
    </div>
  );
}

export default async function Home() {
  try {
    const session = await auth();
    const user = session?.user ?? null;

    return (
      <main className={styles.main}>
        <header className={styles.hero}>
          <div>
            <h1 className={styles.title}>LLMHive Orchestration Studio</h1>
            <p className={styles.subtitle}>
              Assemble elite model ensembles, experiment with advanced reasoning patterns, and
              stream the synthesis in real time—just like the next evolution of ChatGPT.
            </p>
          </div>
          <div>{user ? <SignOut user={user} /> : <SignIn />}</div>
        </header>

        <div className={styles.content}>
          {user ? (
            <Suspense fallback={<div className={styles.loading}>Loading orchestration cockpit…</div>}>
              <PromptForm userId={user.email ?? user.id ?? "guest"} userName={user.name} />
            </Suspense>
          ) : (
            <div className={styles.signInPanel}>
              <p className={styles.signInMessage}>
                Sign in to craft prompts, choose your dream team of frontier models, and unleash
                LLMHive’s collaborative intelligence.
              </p>
            </div>
          )}
        </div>
      </main>
    );
  } catch (error) {
    console.error("Home page error:", error);
    return (
      <main className={styles.main}>
        <header className={styles.hero}>
          <div>
            <h1 className={styles.title}>LLMHive Orchestration Studio</h1>
            <p className={styles.subtitle}>Experience next-generation collaborative intelligence.</p>
          </div>
        </header>
        <div className={styles.content}>
          <p className={styles.error}>
            An error occurred while loading the page. Please try again later.
          </p>
        </div>
      </main>
    );
  }
}
