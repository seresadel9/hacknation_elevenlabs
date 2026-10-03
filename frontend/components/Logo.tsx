export function Logo({ size = 22 }: { size?: number }) {
  // An eclipse: a dark disc with a thin ring of light — "learn in the quiet, master in the light".
  return (
    <svg className="brand-mark" width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <defs>
        <radialGradient id="umbra-corona" cx="50%" cy="50%" r="50%">
          <stop offset="70%" stopColor="#4FE3FF" stopOpacity="0" />
          <stop offset="86%" stopColor="#4FE3FF" stopOpacity="0.9" />
          <stop offset="100%" stopColor="#4FE3FF" stopOpacity="0" />
        </radialGradient>
      </defs>
      <circle cx="16" cy="16" r="15" fill="url(#umbra-corona)" />
      <circle cx="17.5" cy="15" r="11" fill="#0A0B0F" />
    </svg>
  );
}
