const SUN_ICON = "#8a6a2d";
const MOON_ICON = "#3a352e";

function SunIcon() {
  const rays = [0, 45, 90, 135, 180, 225, 270, 315];
  return (
    <svg width="24" height="24" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="5" fill={SUN_ICON} />
      {rays.map((deg) => {
        const rad = (deg * Math.PI) / 180;
        const x1 = 12 + Math.cos(rad) * 7.5;
        const y1 = 12 + Math.sin(rad) * 7.5;
        const x2 = 12 + Math.cos(rad) * 10;
        const y2 = 12 + Math.sin(rad) * 10;
        return (
          <line key={deg} x1={x1} y1={y1} x2={x2} y2={y2} stroke={SUN_ICON} strokeWidth="1.75" strokeLinecap="round" />
        );
      })}
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24">
      <mask id="moonMask">
        <rect x="0" y="0" width="24" height="24" fill="white" />
        <circle cx="14.5" cy="8.5" r="6" fill="black" />
      </mask>
      <circle cx="12" cy="12" r="7" fill={MOON_ICON} mask="url(#moonMask)" />
    </svg>
  );
}

export default function ThemeToggle({ theme, onChange }) {
  return (
    <button
      type="button"
      onClick={() => onChange(theme === "dark" ? "light" : "dark")}
      aria-label={theme === "dark" ? "Switch to day mode" : "Switch to night mode"}
      className="flex h-10 w-10 items-center justify-center rounded-full outline-none
                 transition-colors hover:bg-surface focus-visible:ring-2 focus-visible:ring-felt/50"
    >
      {theme === "dark" ? <SunIcon /> : <MoonIcon />}
    </button>
  );
}
