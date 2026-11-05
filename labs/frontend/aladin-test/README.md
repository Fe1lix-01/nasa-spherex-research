<<<<<<< HEAD
This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
=======
# ÉTER · Visor espectral SPHEREx (frontend)

Frontend del proyecto NASA Space Apps 2026, reto "Planeta X y SPHEREx". Una herramienta web
para explorar las 102 bandas infrarrojas de SPHEREx y mostrar el movimiento de objetos entre
épocas (el satélite cubre el cielo cada ~6 meses; trabajamos con 3 épocas).

## Cómo correrlo

```bash
npm install
npm run dev      # http://localhost:3000 (usa localhost, no la IP de red)
npm run build    # compila y revisa tipos
```

## Estructura

```
src/
├── app/            Rutas de Next.js (layout, page, estilos globales). Solo ensambla.
├── providers/      Proveedores globales (MUI + tema).
├── theme/          Tema de MUI y colores de marca (tokens "eter").
├── components/     Piezas compartidas sin lógica de negocio (íconos).
├── features/       Una carpeta por funcionalidad:
│   ├── viewer/       Visor espectral: componentes, hooks y engine (canvas).
│   ├── menu/         Menú lateral con ayuda y secciones.
│   └── phenomena/    Datos e ilustraciones de los fenómenos.
├── contracts/      Tipos del contrato de datos con el back (BORRADOR).
├── mocks/          JSON simulados que cumplen el contrato.
└── services/       Capa de acceso a datos: mock o back real.
```

Reglas de la estructura:

- Los componentes visuales no piden datos directamente: usan `skyData` de `src/services`.
- `ViewerShell` recibe el fondo por una "ranura" (`background`), así el fondo puede cambiarse
  (por ejemplo, por un mosaico de Aladin Lite) sin tocar los controles.
- La lógica va en hooks (`hooks/`) y el dibujo en `engine/`, separados de los componentes.

## Datos: simulados o reales

Por defecto la app usa los JSON de `src/mocks`. Para usar el back real, crea `.env.local`:

```
NEXT_PUBLIC_USE_MOCK=false
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Los tipos de `src/contracts` son un borrador. Hay que acordarlos con el back; después se
ajustan `src/contracts` y `src/mocks`, y TypeScript indica qué más cambiar.
>>>>>>> develop
