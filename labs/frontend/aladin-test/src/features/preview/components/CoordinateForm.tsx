"use client";

import { useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

type Props = { onSearch: (ra: number, dec: number) => void };

/** Campos para escribir RA y Dec en grados decimales, por ejemplo 209.42 y 53.94. */
export default function CoordinateForm({ onSearch }: Props) {
  const [ra, setRa] = useState("");
  const [dec, setDec] = useState("");
  const [error, setError] = useState<string | null>(null);

  const submit = () => {
    const r = Number(ra);
    const d = Number(dec);
    if (ra.trim() === "" || dec.trim() === "" || Number.isNaN(r) || Number.isNaN(d)) {
      setError("Escribe RA y Dec en grados decimales, por ejemplo 209.42 y 53.94.");
      return;
    }
    if (r < 0 || r >= 360 || d < -90 || d > 90) {
      setError("RA debe estar entre 0 y 360, y Dec entre -90 y 90.");
      return;
    }
    setError(null);
    onSearch(r, d);
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1, maxWidth: 720, mx: "auto", width: "100%" }}>
      <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
        <TextField label="RA (grados)" value={ra} onChange={(e) => setRa(e.target.value)} size="small" sx={{ flex: 1 }} />
        <TextField label="Dec (grados)" value={dec} onChange={(e) => setDec(e.target.value)} size="small" sx={{ flex: 1 }} />
        <Button variant="contained" onClick={submit}>
          Buscar
        </Button>
      </Box>
      {error && (
        <Typography variant="body2" color="error">
          {error}
        </Typography>
      )}
    </Box>
  );
}
