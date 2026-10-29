import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import Providers from "@/providers/Providers";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "ÉTER · Visor espectral SPHEREx",
  description:
    "Visor divulgativo de imágenes infrarrojas con filtros de banda e intensidad de luz. Proyecto Morley.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

// LayoutProps es un tipo global que Next 16 genera solo al correr `next dev`
export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    // inter.variable define --font-inter, que usa el tema de MUI (src/theme/theme.ts)
    <html lang="es" className={inter.variable}>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
