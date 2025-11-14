"use client";

import { ReactNode, useMemo, useState } from "react";
import styles from "./Sidebar.module.css";

const NAVIGATION_SECTIONS: Array<{
  title: string;
  items: Array<{
    label: string;
    description: string;
    icon: ReactNode;
  }>;
}> = [
  {
    title: "Workspace",
    items: [
      {
        label: "New Orchestration",
        description: "Spin up a fresh hive of collaborating agents.",
        icon: (
          <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path
              d="M12 5v14m7-7H5"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        ),
      },
      {
        label: "All Sessions",
        description: "Revisit previous orchestration timelines.",
        icon: (
          <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path
              d="M6 7h12M6 12h12M6 17h7"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        ),
      },
      {
        label: "Model Library",
        description: "Browse and compare your connected LLMs.",
        icon: (
          <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path
              d="M6.5 5h11l.5 2v12l-6 2-6-2V7z"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        ),
      },
    ],
  },
  {
    title: "Reasoning",
    items: [
      {
        label: "Strategy Lab",
        description: "Prototype advanced reasoning flows.",
        icon: (
          <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path
              d="M12 5.5l6.5 3.75V18L12 21.5 5.5 18V9.25z"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        ),
      },
      {
        label: "Observatory",
        description: "Inspect signals, telemetry, and feedback.",
        icon: (
          <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path
              d="M4.5 12a7.5 7.5 0 0115 0 7.5 7.5 0 01-15 0zm0 0h15M9 12a3 3 0 106 0 3 3 0 00-6 0z"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        ),
      },
    ],
  },
  {
    title: "Support",
    items: [
      {
        label: "Settings",
        description: "Manage providers, teams, and billing.",
        icon: (
          <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path
              d="M12 15a3 3 0 100-6 3 3 0 000 6zm8.5-3.5l-2.2-.5a7.56 7.56 0 00-.6-1.4l1.2-1.9-1.4-1.4-1.9 1.2c-.45-.26-.92-.47-1.42-.6l-.5-2.2h-2l-.5 2.2a7.56 7.56 0 00-1.4.6l-1.9-1.2-1.4 1.4 1.2 1.9c-.26.45-.47.92-.6 1.42l-2.2.5v2l2.2.5c.13.5.34.97.6 1.42l-1.2 1.9 1.4 1.4 1.9-1.2c.45.26.92.47 1.42.6l.5 2.2h2l.5-2.2c.5-.13.97-.34 1.42-.6l1.9 1.2 1.4-1.4-1.2-1.9c.26-.45.47-.92.6-1.42l2.2-.5v-2z"
              strokeWidth="1.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        ),
      },
      {
        label: "Support Hub",
        description: "Guides, changelog, and community help.",
        icon: (
          <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path
              d="M12 21c4.97 0 9-3.806 9-8.5S16.97 4 12 4 3 7.806 3 12.5c0 2.8 1.5 5.29 3.82 6.86L6 21l3.24-1.26A10.1 10.1 0 0012 21z"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        ),
      },
    ],
  },
];

export default function Sidebar({
  displayName,
}: {
  displayName?: string | null;
}) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const initials = useMemo(() => {
    if (!displayName) return "LL";
    const parts = displayName.trim().split(/\s+/);
    if (parts.length === 1) {
      return parts[0].slice(0, 2).toUpperCase();
    }
    return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
  }, [displayName]);

  return (
    <aside className={`${styles.sidebar} ${isCollapsed ? styles.collapsed : ""}`}>
      <div className={styles.brandRow}>
        <button
          type="button"
          className={styles.collapseButton}
          onClick={() => setIsCollapsed((value) => !value)}
          aria-label={isCollapsed ? "Expand navigation" : "Collapse navigation"}
        >
          <span />
          <span />
          <span />
        </button>
        <span className={styles.brand}>LLMHive</span>
      </div>

      <button type="button" className={styles.newChatButton}>
        <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
          <path
            d="M12 5v14m7-7H5"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        <span>New orchestration</span>
      </button>

      <div className={styles.sectionList}>
        {NAVIGATION_SECTIONS.map((section) => (
          <div key={section.title} className={styles.section}>
            <span className={styles.sectionTitle}>{section.title}</span>
            <ul>
              {section.items.map((item) => (
                <li key={item.label}>
                  <button type="button" className={styles.navItem}>
                    <span className={styles.icon}>{item.icon}</span>
                    <span className={styles.navCopy}>
                      <span>{item.label}</span>
                      <small>{item.description}</small>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <div className={styles.profileCard}>
        <div className={styles.avatar}>{initials}</div>
        <div className={styles.profileCopy}>
          <span className={styles.profileName}>{displayName ?? "Guest Innovator"}</span>
          <small>Orchestration Studio</small>
        </div>
      </div>
    </aside>
  );
}
