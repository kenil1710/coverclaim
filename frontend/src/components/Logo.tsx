/**
 * The mark: a shield with a crack running through it, and the crack being
 * sealed by an orange seam. Obsidian body, signal-orange seal.
 */
export function Logomark({ size = 32, animated = false }: { size?: number; animated?: boolean }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none" aria-hidden="true">
      <defs>
        <linearGradient id="cc-shield" x1="10" y1="4" x2="54" y2="60" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#2a2a36" />
          <stop offset="1" stopColor="#121218" />
        </linearGradient>
        <linearGradient id="cc-seal" x1="30" y1="24" x2="34" y2="56" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#ffb07f" />
          <stop offset="1" stopColor="#ff6b2c" />
        </linearGradient>
      </defs>
      <path
        d="M32 4 L54 12 V30 C54 44.5 44.6 55.2 32 60 C19.4 55.2 10 44.5 10 30 V12 Z"
        fill="url(#cc-shield)"
        stroke="#ff6b2c"
        strokeWidth="2.5"
        strokeLinejoin="round"
      />
      <path
        d="M33 7 L28 18 L36 26 L29 36 L35 45 L31 58"
        stroke="#050507"
        strokeWidth="4.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      <path
        d="M36 26 L29 36 L35 45 L31 58"
        stroke="url(#cc-seal)"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
        style={
          animated
            ? { strokeDasharray: 48, strokeDashoffset: 48, animation: "cc-seal 1.4s 0.2s ease-out forwards" }
            : undefined
        }
      />
      <path
        d="M28.5 31 L36.5 31 M28 40.5 L36 40.5 M29 51 L37 51"
        stroke="#ff6b2c"
        strokeWidth="2"
        strokeLinecap="round"
        style={animated ? { opacity: 0, animation: "cc-fade 0.4s 1.4s ease-out forwards" } : undefined}
      />
      <style>{`@keyframes cc-seal { to { stroke-dashoffset: 0; } } @keyframes cc-fade { to { opacity: 1; } }`}</style>
    </svg>
  );
}

export function Wordmark({ size = 30 }: { size?: number }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 10 }}>
      <Logomark size={size} />
      <span
        style={{
          fontFamily: "var(--font-head)",
          fontWeight: 700,
          fontSize: size * 0.62,
          letterSpacing: "-0.02em",
        }}
      >
        Cover<span style={{ color: "var(--orange)" }}>Claim</span>
      </span>
    </span>
  );
}
