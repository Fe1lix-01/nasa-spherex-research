import type { ReactNode } from "react";

const CRYSTAL = "M0-6 L5-3 L5 3 L0 6 L-5 3 L-5-3Z";

const ART: Record<string, ReactNode> = {
  nebulosa: (
      <svg viewBox="0 0 320 180" preserveAspectRatio="xMidYMid slice" style={{ width: "100%", height: "100%" }}>
        <rect width="320" height="180" fill="#04050a" />
        <g filter="url(#blur6)">
          <ellipse cx="120" cy="90" rx="90" ry="45" fill="#c2309b" opacity=".6" />
          <ellipse cx="190" cy="80" rx="80" ry="40" fill="#2fb8c9" opacity=".5" />
          <ellipse cx="160" cy="112" rx="60" ry="28" fill="#ff7a59" opacity=".45" />
        </g>
        <g fill="#fff">
          <circle cx="40" cy="30" r="1.3" />
          <circle cx="270" cy="40" r="1.1" />
          <circle cx="90" cy="150" r="1.2" />
          <circle cx="240" cy="140" r="1.4" />
          <circle cx="160" cy="25" r="1" />
          <circle cx="300" cy="110" r="1" />
        </g>
      </svg>
    ),
  galaxias: (
      <svg viewBox="0 0 320 180" preserveAspectRatio="xMidYMid slice" style={{ width: "100%", height: "100%" }}>
        <rect width="320" height="180" fill="#04050a" />
        <g transform="rotate(-25 160 90)">
          <ellipse cx="160" cy="90" rx="135" ry="36" fill="url(#gGal)" />
          <g filter="url(#blur2)" fill="none" stroke="#9db4ff" strokeWidth="4" opacity=".7">
            <path d="M30 90 C70 45 130 45 160 90 S250 135 290 90" />
            <path d="M30 90 C70 135 130 135 160 90 S250 45 290 90" />
          </g>
          <ellipse cx="160" cy="90" rx="18" ry="11" fill="#fff2c4" filter="url(#blur2)" />
        </g>
        <g fill="#fff">
          <circle cx="30" cy="30" r="1.2" />
          <circle cx="290" cy="150" r="1.2" />
          <circle cx="280" cy="30" r="1" />
        </g>
      </svg>
    ),
  protoestrellas: (
      <svg viewBox="0 0 320 180" preserveAspectRatio="xMidYMid slice" style={{ width: "100%", height: "100%" }}>
        <rect width="320" height="180" fill="#04050a" />
        <path d="M160 95 L148 6 L172 6Z" fill="#7fd0ff" opacity=".35" filter="url(#blur2)" />
        <path d="M160 95 L148 174 L172 174Z" fill="#7fd0ff" opacity=".35" filter="url(#blur2)" />
        <ellipse cx="160" cy="95" rx="125" ry="15" fill="#ff8a3d" opacity=".55" filter="url(#blur2)" />
        <ellipse cx="160" cy="95" rx="75" ry="7" fill="#ffd199" />
        <circle cx="160" cy="95" r="14" fill="url(#gStar)" />
      </svg>
    ),
  hielos: (
      <svg viewBox="0 0 320 180" preserveAspectRatio="xMidYMid slice" style={{ width: "100%", height: "100%" }}>
        <rect width="320" height="180" fill="#0b1a2e" />
        <ellipse cx="160" cy="90" rx="150" ry="85" fill="url(#gDark)" />
        <g fill="#9ff0ff" opacity=".9">
          <path d={CRYSTAL} transform="translate(110 78) scale(1.4)" />
          <path d={CRYSTAL} transform="translate(150 105) scale(1)" />
          <path d={CRYSTAL} transform="translate(195 80) scale(1.6)" />
          <path d={CRYSTAL} transform="translate(225 115) scale(.9)" />
          <path d={CRYSTAL} transform="translate(130 130) scale(.8)" />
        </g>
      </svg>
    ),
  cometas: (
      <svg viewBox="0 0 320 180" preserveAspectRatio="xMidYMid slice" style={{ width: "100%", height: "100%" }}>
        <rect width="320" height="180" fill="#04050a" />
        <polygon points="250,70 20,150 30,168 258,88" fill="url(#gTail)" filter="url(#blur2)" />
        <polygon points="250,70 70,112 78,134 258,88" fill="#ffd9a0" opacity=".35" filter="url(#blur2)" />
        <circle cx="254" cy="79" r="14" fill="url(#gStar)" />
        <circle cx="254" cy="79" r="3" fill="#fff" />
        <g fill="#fff">
          <circle cx="50" cy="30" r="1.2" />
          <circle cx="200" cy="25" r="1" />
          <circle cx="290" cy="150" r="1.2" />
        </g>
      </svg>
    ),
  estructura: (
      <svg viewBox="0 0 320 180" preserveAspectRatio="xMidYMid slice" style={{ width: "100%", height: "100%" }}>
        <rect width="320" height="180" fill="#05030f" />
        <g stroke="#6a5cff" strokeOpacity=".4" fill="none">
          <path d="M20 40 L90 80 L160 50 L230 100 L300 60" />
          <path d="M90 80 L120 140 L200 150 L230 100" />
          <path d="M160 50 L190 18" />
          <path d="M20 40 L40 120 L120 140" />
        </g>
        <g fill="#d9d4ff">
          <circle cx="20" cy="40" r="3" />
          <circle cx="90" cy="80" r="4" />
          <circle cx="160" cy="50" r="3.5" />
          <circle cx="230" cy="100" r="4" />
          <circle cx="300" cy="60" r="3" />
          <circle cx="120" cy="140" r="3" />
          <circle cx="200" cy="150" r="3" />
          <circle cx="190" cy="18" r="2.5" />
          <circle cx="40" cy="120" r="2.5" />
        </g>
        <g fill="#8d85ff" opacity=".7">
          <circle cx="60" cy="70" r="1" />
          <circle cx="130" cy="90" r="1" />
          <circle cx="260" cy="130" r="1" />
          <circle cx="180" cy="110" r="1" />
          <circle cx="280" cy="30" r="1" />
          <circle cx="100" cy="30" r="1" />
        </g>
      </svg>
    ),
};

export default function PhenomenonArt({ id }: { id: string }) {
  return <>{ART[id] ?? null}</>;
}