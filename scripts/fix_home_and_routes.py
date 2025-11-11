import os, re, time, shutil
from pathlib import Path

repo = Path.cwd()
ui_app = repo / "ui" / "app"
layout = ui_app / "layout.tsx"
page   = ui_app / "page.tsx"

if not ui_app.exists():
    print("❌ ui/app not found. Run this from your repo root.")
    raise SystemExit(1)

# --- determine auth import, by looking at your real layout.tsx ---
auth_import = "@/auth"  # safe default
if layout.exists():
    try:
        t = layout.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"""import\s*\{\s*auth\s*\}\s*from\s*['"]([^'"]+)['"]""", t)
        if m:
            auth_import = m.group(1)
            print(f"🔎 auth import detected from layout.tsx: {auth_import}")
        else:
            print("ℹ️  Could not find `import { auth }` in layout.tsx, using '@/auth'.")
    except Exception as e:
        print(f"ℹ️  Unable to read layout.tsx ({e}); using '@/auth'.")
else:
    print("ℹ️  layout.tsx not found, using '@/auth'.")

# --- ensure LoginPage exists (minimal, motion-safe) ---
login_file = ui_app / "components" / "LoginPage.tsx"
if not login_file.exists():
    login_file.parent.mkdir(parents=True, exist_ok=True)
    login_file.write_text(
        "'use client';\n\n"
        "export default function LoginPage() {\n"
        "  return (\n"
        "    <div className=\"min-h-[60vh] grid place-items-center\">\n"
        "      <div className=\"rounded-xl border border-border bg-panel p-8 text-center max-w-sm w-full\">\n"
        "        <h1 className=\"text-xl font-semibold\">Sign in</h1>\n"
        "        <p className=\"mt-2 text-text-dim text-sm\">You need to sign in to continue.</p>\n"
        "        <a\n"
        "          href=\"/api/auth/signin\"\n"
        "          className=\"mt-4 inline-flex justify-center rounded-lg bg-gold text-bg px-4 py-2\"\n"
        "        >\n"
        "          Sign in with GitHub\n"
        "        </a>\n"
        "      </div>\n"
        "    </div>\n"
        "  );\n"
        "}\n",
        encoding="utf-8"
    )
    print(f"🆕 Created {login_file.relative_to(repo)}")
else:
    print(f"✓ Found {login_file.relative_to(repo)}")

# --- write ui/app/page.tsx with correct imports (relative paths!) ---
page_backup = None
if page.exists():
    page_backup = page.with_suffix(f".tsx.bak.{int(time.time())}")
    shutil.copy2(page, page_backup)
    print(f"🗂  Backup saved: {page_backup.relative_to(repo)}")

page_content = f"""import AppShell from './components/AppShell';
import ChatSurface from './components/ChatSurface';
import LoginPage from './components/LoginPage';
import {{ auth }} from '{auth_import}';

export default async function Page() {{
  const session = await auth?.();
  if (!session?.user) {{
    return <LoginPage />;
  }}
  return (
    <AppShell title="Chat">
      <div className="mx-auto max-w-4xl">
        <ChatSurface />
      </div>
    </AppShell>
  );
}}
"""
page.write_text(page_content, encoding="utf-8")
print(f"✅ Wrote {page.relative_to(repo)}")

# --- create top-level pages to avoid 404s on sidebar links ---
routes = ["dashboard","workflows","datasets","providers","analytics","settings","model-comparison"]

def to_component_name(route: str) -> str:
    # dashboard -> Dashboard, model-comparison -> ModelComparison
    parts = re.split(r"[-_]", route)
    return "".join(p[:1].upper() + p[1:] for p in parts)

for r in routes:
    d = ui_app / r
    d.mkdir(parents=True, exist_ok=True)
    f = d / "page.tsx"
    if not f.exists():
        component = to_component_name(r)
        f.write_text(
            "import AppShell from '../components/AppShell';\n"
            "import LoginPage from '../components/LoginPage';\n"
            f"import {{ auth }} from '{auth_import}';\n\n"
            f"export default async function {component}Page() {{\n"
            "  const session = await auth?.();\n"
            "  if (!session?.user) {\n"
            "    return <LoginPage />;\n"
            "  }\n"
            "  return (\n"
            f"    <AppShell title=\"{r.replace('-', ' ').title()}\">\n"
            "      <div className=\"mx-auto max-w-4xl text-text-dim py-10\">\n"
            f"        <p>{r.replace('-', ' ').title()} coming soon…</p>\n"
            "      </div>\n"
            "    </AppShell>\n"
            "  );\n"
            "}\n",
            encoding="utf-8"
        )
        print(f"🆕 Created {f.relative_to(repo)}")
    else:
        print(f"✓ Exists {f.relative_to(repo)}")

print("🎯 Done.")
