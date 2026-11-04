import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { FILTERS_INTRO } from "@/features/menu/content";
import type { FilterDef } from "@/features/viewer/types";
import { eter } from "@/theme/theme";

export default function FiltersContent({ filters, active }: { filters: FilterDef[]; active: number }) {
  return (
    <Box>
      <Typography sx={{ fontSize: 15, lineHeight: 1.7, color: "rgba(255,255,255,0.7)" }}>{FILTERS_INTRO}</Typography>
      <Box component="ul" sx={{ listStyle: "none", p: 0, m: 0, mt: 3 }}>
        {filters.map((f, i) => {
          const on = i === active;
          return (
            <Box
              component="li"
              key={f.id}
              sx={{ py: 2, borderBottom: `1px solid ${eter.line}`, "&:last-of-type": { borderBottom: 0 } }}
            >
              <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 1.5 }}>
                <Typography
                  component="p"
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 1,
                    fontSize: 16,
                    color: on ? "primary.main" : "text.primary",
                  }}
                >
                  {on && (
                    <Box
                      component="span"
                      sx={{ width: 6, height: 6, borderRadius: "50%", backgroundColor: "primary.main" }}
                    />
                  )}
                  {f.name}
                </Typography>
                <Typography sx={{ flexShrink: 0, fontSize: 14, color: "text.disabled" }}>{f.band}</Typography>
              </Box>
              <Typography sx={{ mt: 0.75, fontSize: 15, lineHeight: 1.7, color: "rgba(255,255,255,0.6)" }}>
                {f.desc}
                {on && " Banda activa del visor."}
              </Typography>
            </Box>
          );
        })}
      </Box>
    </Box>
  );
}