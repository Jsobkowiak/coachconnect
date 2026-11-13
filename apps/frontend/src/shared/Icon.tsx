import type { CSSProperties } from "react";
export type IconName =
  | "blocks"
  | "workout"
  | "exercise"
  | "arrow"
  | "plus"
  | "clock"
  | "calendar"
  | "trophy"
  | "check"
  | "more"
  | "sun"
  | "moon"
  | "chevron"
  | "activity"
  | "chart"
  | "account";
const paths: Record<IconName, string[]> = {
  blocks: ["M3 3h7v7H3z", "M14 3h7v7h-7z", "M3 14h7v7H3z", "M14 14h7v7h-7z"],
  workout: ["M6 8v8M3 10v4M18 8v8M21 10v4M6 12h12"],
  exercise: ["M4 5h16v15H4z", "M8 2v6M16 2v6M8 12h8M8 16h5"],
  arrow: ["M5 12h14M13 6l6 6-6 6"],
  plus: ["M12 5v14M5 12h14"],
  clock: ["M12 8v4l3 2", "M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0"],
  calendar: ["M4 5h16v16H4zM4 10h16M8 3v4M16 3v4"],
  trophy: [
    "M8 3h8v6a4 4 0 0 1-8 0zM8 5H4v3a4 4 0 0 0 4 4M16 5h4v3a4 4 0 0 1-4 4M12 13v5M8 21h8M9 18h6",
  ],
  check: ["M5 12l4 4L19 6"],
  more: ["M5 12h.01M12 12h.01M19 12h.01"],
  sun: [
    "M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6 1.4 1.4M17 17l1.4 1.4M5.6 18.4 1.4-1.4M17 7l1.4-1.4",
    "M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0",
  ],
  moon: ["M20 15a8.5 8.5 0 0 1-11-11A8.5 8.5 0 1 0 20 15z"],
  chevron: ["M9 5l7 7-7 7"],
  account: ["M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0", "M4 21v-2a8 8 0 0 1 16 0v2"],
  chart: ["M3 3v18h18", "M7 14l4-5 4 3 6-8"],
  activity: ["M3 12h4l3-8 4 16 3-8h4"],
};
export function Icon({
  name,
  size = 20,
  style,
}: {
  name: IconName;
  size?: number;
  style?: CSSProperties;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      style={style}
    >
      {paths[name].map((d, i) => (
        <path key={i} d={d} />
      ))}
    </svg>
  );
}
