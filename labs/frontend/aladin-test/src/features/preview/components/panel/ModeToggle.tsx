"use client";

import SegmentedControl from "@/components/SegmentedControl/SegmentedControl";
import { eter } from "@/theme/theme";

export type ViewMode = "sky" | "epochs";

type Props = {
  value: ViewMode;
  onChange: (mode: ViewMode) => void;
};

const OPTIONS = [
  { value: "sky", label: "Mosaico del cielo" },
  { value: "epochs", label: "Épocas simuladas" },
] as const;

/** Cambia entre el mosaico del cielo (Aladin) y las épocas simuladas con animación. */
export default function ModeToggle({ value, onChange }: Props) {
  return (
    <SegmentedControl
      value={value}
      onChange={onChange}
      options={OPTIONS}
      ariaLabel="Modo de vista"
      sx={{ alignSelf: "flex-start", bgcolor: eter.panelGlass, backdropFilter: "blur(10px)" }}
    />
  );
}