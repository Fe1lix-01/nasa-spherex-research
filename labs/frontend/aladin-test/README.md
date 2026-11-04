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