import type { JSX } from "solid-js";

export type StudioIconName =
  | "home"
  | "project"
  | "workspace"
  | "agents"
  | "context"
  | "capabilities"
  | "semantic"
  | "diagnostics"
  | "command"
  | "search"
  | "sun"
  | "moon"
  | "check"
  | "minus";

const paths: Record<StudioIconName, JSX.Element> = {
  home: <><path d="M3 10.5 12 3l9 7.5"/><path d="M5.5 9.5V21h13V9.5"/><path d="M9.5 21v-7h5v7"/></>,
  project: <><path d="M3.5 6.5h6l2 2H20.5v10a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2z"/><path d="M3.5 9h17"/></>,
  workspace: <><path d="M4 20h4l11-11a2.1 2.1 0 0 0-4-4L4 16z"/><path d="m13.5 6.5 4 4"/><path d="M4 20h16"/></>,
  agents: <><path d="M8 8a4 4 0 1 1 8 0"/><rect x="5" y="8" width="14" height="11" rx="3"/><path d="M9 13h.01"/><path d="M15 13h.01"/><path d="M9 16h6"/><path d="M12 3V1.5"/></>,
  context: <><rect x="4" y="4" width="16" height="16" rx="4"/><path d="M8 9h8"/><path d="M8 12h5"/><path d="M8 15h7"/></>,
  capabilities: <><rect x="4" y="4" width="6" height="6" rx="1.5"/><rect x="14" y="4" width="6" height="6" rx="1.5"/><rect x="4" y="14" width="6" height="6" rx="1.5"/><rect x="14" y="14" width="6" height="6" rx="1.5"/></>,
  semantic: <><circle cx="6" cy="12" r="2.5"/><circle cx="18" cy="6" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="m8.2 10.9 7.6-3.8"/><path d="m8.2 13.1 7.6 3.8"/></>,
  diagnostics: <><path d="M3 12h4l2-5 4 10 2-5h6"/><path d="M5 20h14"/></>,
  command: <path d="M9 7H7a3 3 0 1 1 3-3v16a3 3 0 1 1-3-3h10a3 3 0 1 1-3 3V4a3 3 0 1 1 3 3H9Z"/>,
  search: <><circle cx="11" cy="11" r="6.5"/><path d="m16 16 4.5 4.5"/></>,
  sun: <><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.42 1.42"/><path d="m17.65 17.65 1.42 1.42"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m4.93 19.07 1.42-1.42"/><path d="m17.65 6.35 1.42-1.42"/></>,
  moon: <path d="M20 15.5A8 8 0 0 1 8.5 4 8.5 8.5 0 1 0 20 15.5Z"/>,
  check: <path d="m5 12 4 4L19 6"/>,
  minus: <path d="M6 12h12"/>,
};

export function StudioIcon(props: { name: StudioIconName; class?: string }) {
  return (
    <svg
      class={props.class}
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="1.75"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
    >
      {paths[props.name]}
    </svg>
  );
}
