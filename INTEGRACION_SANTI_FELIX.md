# Integración científica temporal

La rama temporal parte de `dev_kevin` en 44574ed. Se revisaron las referencias remotas `dev_santi` en 3f597b7 y `dev_felix` en af077b5. La rama de Félix incluye trabajo anterior de Santi y del visor, ya presente en la base local. Los archivos nuevos seleccionados se integraron sin modificar las ramas originales.

## Archivos y alcance

- Santi: `labs/science/02_visualizar_canal.py` y `11_01_inspeccionar_cubo.py` exploran el cubo de M101. La figura `outputs/11_m101_canal_63.png` muestra imagen, cobertura y máscara. Se entrega mediante `GET /api/v1/science/m101/channel-63/preview`.
- Félix: `labs/science/06_barnard_consultar_irsa.py` y `06b_barnard_sia.py` exploran búsquedas de Barnard. El endpoint existente `GET /api/v1/irsa/observations` cubre la consulta TAP por posición y detector. La búsqueda SIA es un flujo adicional que no se ha integrado.
- El espectro y mapa de PAH de Félix necesitan el cubo FITS M101. Sus scripts son exploratorios. El mapa no representa variación temporal y no debe utilizarse como detección calibrada de PAH.
- El script anterior `zogy_script.py` necesita `P_D` y `D` y no es importable de forma independiente. Requiere definir entradas científicas y validación antes de conectarlo.
- El visor de movimiento espera imágenes por época, geometría espacial y contratos que el backend aún no suministra. La página `/science` muestra únicamente la figura exploratoria M101. No usa el mapeo de coordenadas del visor de movimiento.

## Ejecución

Desde `apps/science-api`, iniciar `python -m uvicorn app.main:app --port 8000` con el entorno Python del proyecto. Desde `labs/frontend/aladin-test`, instalar las dependencias con `npm ci` e iniciar `npm run dev`. Abrir `http://localhost:3000/science`. La ruta de Next.js usa `SCIENCE_API_URL`, cuyo valor por defecto es `http://127.0.0.1:8000`.

La consulta IRSA para Barnard se hace con `GET /api/v1/irsa/observations?ra=269.44627&dec=4.7682&band=SPHEREx-D2&limit=2`. La posición es aproximada para 2026 y no incorpora una predicción astrométrica precisa.

## Comprobaciones

- Backend: 38 pruebas aprobadas, incluida entrega de imagen y error 503 si falta.
- Consulta real IRSA: HTTP 200 y dos registros en D2 para los parámetros de Barnard. Resultado sujeto a disponibilidad y cambios del archivo.
- Frontend: ESLint sobre los archivos nuevos y `next typegen` seguido de `tsc --noEmit` sin errores.
- Prueba local HTTP con FastAPI y Next.js: la página `/science` incluyó la ruta de imagen y el PNG devuelto por Next.js fue idéntico al del backend.

El proyecto requiere datos FITS y dependencias científicas para generar nuevos resultados. El PNG incorporado es un producto estático, no una ejecución dinámica del análisis.
