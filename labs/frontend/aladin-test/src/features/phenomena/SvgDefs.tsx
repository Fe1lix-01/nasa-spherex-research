/** Definiciones SVG compartidas (gradientes y desenfoques) por las ilustraciones. */
export function SvgDefs() {
  return (
    <svg width="0" height="0" style={{ position: "absolute" }} aria-hidden="true">
      <defs>
        <filter id="blur6">
          <feGaussianBlur stdDeviation="6" />
        </filter>
        <filter id="blur2">
          <feGaussianBlur stdDeviation="2" />
        </filter>
        <radialGradient id="gGal">
          <stop offset="0" stopColor="#fff6d8" />
          <stop offset=".3" stopColor="#ffd48a" stopOpacity=".85" />
          <stop offset="1" stopColor="#5b7bff" stopOpacity="0" />
        </radialGradient>
        <radialGradient id="gStar">
          <stop offset="0" stopColor="#fff" />
          <stop offset="1" stopColor="#ffb347" stopOpacity="0" />
        </radialGradient>
        <radialGradient id="gDark">
          <stop offset="0" stopColor="#020308" />
          <stop offset="1" stopColor="#0b1a2e" stopOpacity="0" />
        </radialGradient>
        <linearGradient id="gTail" x1="1" x2="0">
          <stop offset="0" stopColor="#bfe9ff" stopOpacity=".9" />
          <stop offset="1" stopColor="#bfe9ff" stopOpacity="0" />
        </linearGradient>
      </defs>
    </svg>
  );
}