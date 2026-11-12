# Integración científica temporal

La rama temporal parte de `dev_kevin` en 44574ed. Se revisaron las referencias remotas `dev_santi` en 3f597b7 y `dev_felix` en af077b5. La rama de Félix incluye trabajo anterior de Santi y del visor, ya presente en la base local. Los archivos nuevos seleccionados se integraron sin modificar las ramas originales.

## Archivos y alcance

- Santi: `app/services/m101.py` genera la figura del canal 63 desde el FITS configurado mediante `M101_FITS_PATH`. El endpoint `GET /api/v1/science/m101/channel-63/preview` devuelve la imagen, cobertura y máscara. La práctica `labs/science/02_visualizar_canal.py` reutiliza el servicio para guardar una copia en `outputs`.
- Félix: `labs/science/06_barnard_consultar_irsa.py` y `06b_barnard_sia.py` exploran búsquedas de Barnard. El endpoint existente `GET /api/v1/irsa/observations` cubre la consulta TAP por posición y detector. El endpoint GET /api/v1/sia/observations ya tuvo una comprobación
manual satisfactoria con QR3. Su integración tiene pruebas y
documentación pendientes..
- El espectro y mapa de PAH de Félix necesitan el cubo FITS M101. Sus scripts son exploratorios. El mapa no representa variación temporal y no debe utilizarse como detección calibrada de PAH.
- El script anterior `zogy_script.py` necesita `P_D` y `D` y no es importable de forma independiente. Requiere definir entradas científicas y validación antes de conectarlo.
- El visor de movimiento espera imágenes por época, geometría espacial y contratos que el backend aún no suministra. La página `/science` muestra únicamente la figura exploratoria M101. No usa el mapeo de coordenadas del visor de movimiento.

## Ejecución

Los siguientes comandos corresponden a PowerShell. Se requiere Python,
Node.js y npm instalados.

### Backend

Desde la raíz del repositorio, crear el entorno virtual si todavía
no existe e instalar las dependencias:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\apps\science-api\requirements.txt
```

Descargar el FITS siguiendo la sección «Configuración local del FITS
de M101». Después, desde la raíz, configurar su ruta absoluta:

```powershell
$env:M101_FITS_PATH = (Resolve-Path -LiteralPath ".\data\m101\M101_irsa.fits").Path
```

Iniciar el backend en esa misma terminal:

```powershell
cd ".\apps\science-api"
..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Swagger está disponible en:

http://127.0.0.1:8000/docs

La vista previa del canal 63 se consulta en:

http://127.0.0.1:8000/api/v1/science/m101/channel-63/preview

### Frontend

Abrir una segunda terminal en la raíz del repositorio:

```powershell
cd ".\labs\frontend\aladin-test"
npm ci
$env:SCIENCE_API_URL = "http://127.0.0.1:8000"
$env:NEXT_PUBLIC_API_URL = "http://127.0.0.1:8000/api/v1"
npm run dev
```

El catálogo está disponible en:

http://localhost:3000/catalog

Si Next.js utiliza otro puerto, abrir ese puerto con la ruta `/catalog`.

`SCIENCE_API_URL` configura la dirección del backend para el proxy
de la figura científica. `NEXT_PUBLIC_API_URL` configura la dirección
de las consultas del catálogo e incluye `/api/v1`.

Las variables se configuran antes de iniciar Next.js. El backend y
el frontend deben permanecer ejecutándose en sus respectivas terminales.

El catálogo muestra únicamente objetos presentes en las observaciones.
M101 recibe su vista científica cuando existe como objeto del catálogo.
Descargar el cubo M101 para el endpoint no agrega observaciones al catálogo.

La página `/science` se conserva como página de pruebas.

La consulta IRSA para Barnard se hace con `GET /api/v1/irsa/observations?ra=269.44627&dec=4.7682&band=SPHEREx-D2&limit=2`. La posición es aproximada para 2026 y no incorpora una predicción astrométrica precisa.

## Comprobaciones

- Backend: 68 pruebas aprobadas, incluidas 22 de visualización científica y 17 del catálogo.
- Consulta real IRSA: HTTP 200 y dos registros en D2 para los parámetros de Barnard. Resultado sujeto a disponibilidad y cambios del archivo.
- Frontend: ESLint sobre los archivos nuevos y `next typegen` seguido de `tsc --noEmit` sin errores.
- Prueba local HTTP con FastAPI y Next.js: la página `/science` incluyó la ruta de imagen y el PNG devuelto por Next.js fue idéntico al del backend.

El proyecto requiere datos FITS y dependencias científicas para generar nuevos resultados. El endpoint de M101 genera la figura del canal 63 desde el FITS indicado por M101_FITS_PATH. La práctica labs/science/02_visualizar_canal.py también permite guardar una copia de la figura en outputs.

## Configuración local del FITS de M101

La vista previa del canal 63 se genera desde el archivo `M101_irsa.fits`.

Fuente del archivo:
https://irsa.ipac.caltech.edu/data/demos/notebooks/spherex/M101_irsa.fits

Los siguientes comandos se ejecutan en PowerShell desde la raíz del repositorio.

### Descargar el archivo

Crear la carpeta local:

```powershell
New-Item -ItemType Directory -Force -Path ".\data\m101"
```

Descargar el FITS y esperar a que el comando termine correctamente:

```powershell
curl.exe --fail --location "https://irsa.ipac.caltech.edu/data/demos/notebooks/spherex/M101_irsa.fits" --output ".\data\m101\M101_irsa.fits"
```

Comprobar la ubicación y el tamaño:

```powershell
Get-Item -LiteralPath ".\data\m101\M101_irsa.fits" | Select-Object FullName, Length
```

El FITS de M101 se guarda localmente en `data/m101/M101_irsa.fits`
y está excluido de Git mediante `.gitignore`. Cada integrante descarga
su propia copia y configura `M101_FITS_PATH` con su ruta absoluta.

El repositorio contiene otros archivos FITS previamente registrados,
utilizados por el catálogo y las prácticas científicas.

### Instalar las dependencias del backend

Si todavía no existe el entorno virtual:

```powershell
py -m venv .venv
```

Instalar las dependencias:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\apps\science-api\requirements.txt
```

### Configurar la ruta absoluta e iniciar el backend

Desde la raíz del repositorio:

```powershell
$env:M101_FITS_PATH = (Resolve-Path -LiteralPath ".\data\m101\M101_irsa.fits").Path
Test-Path -LiteralPath $env:M101_FITS_PATH
```

La comprobación debe devolver `True`.

Iniciar el backend en esa misma terminal:

```powershell
cd ".\apps\science-api"
..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

`M101_FITS_PATH` pertenece a la sesión actual de PowerShell.
Debe configurarse nuevamente al abrir otra terminal para iniciar el servidor.
Este procedimiento configura la variable directamente en PowerShell.

Los archivos `.env` personales están excluidos mediante `.gitignore`.
El ejemplo de configuración se conserva en esta documentación.

### Consultar la vista previa

Con el backend iniciado, abrir:

http://127.0.0.1:8000/api/v1/science/m101/channel-63/preview

La respuesta correcta es HTTP 200 con tipo `image/png`.
La figura contiene la imagen del canal 63, la cobertura y la máscara de calidad.

### Comprobar un archivo inexistente

Detener Uvicorn con Ctrl+C. Desde `apps/science-api`, guardar la
configuración válida y asignar una ruta inexistente:

```powershell
$m101RutaValida = $env:M101_FITS_PATH
$env:M101_FITS_PATH = Join-Path (Split-Path $m101RutaValida) "archivo_inexistente.fits"
Test-Path -LiteralPath $env:M101_FITS_PATH
```

La comprobación debe devolver `False`.

Reiniciar el backend:

```powershell
..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Consultar nuevamente la vista previa. La respuesta esperada es HTTP 503:

```json
{
  "detail": "El archivo científico de M101 no está disponible"
}
```

Después de la prueba, detener Uvicorn y restaurar la configuración:

```powershell
$env:M101_FITS_PATH = $m101RutaValida
..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

### Comprobación local realizada

- Archivo descargado en `data/m101/M101_irsa.fits`.
- Tamaño observado de 87 295 680 bytes.
- `git check-ignore` confirmó que el archivo está ignorado.
- Con la ruta válida, la vista previa cargó correctamente.
- Con una ruta inexistente, el endpoint devolvió HTTP 503 con el mensaje esperado.

## Validación del FITS de M101

Antes de generar la figura, `app/services/m101.py` comprueba:

- El canal solicitado es un entero mayor o igual a 1.
- Existen las extensiones IMAGE, NHITS, FLAGS y SPECTRAL_CHANNELS.
- IMAGE, NHITS y FLAGS contienen cubos tridimensionales sin dimensiones vacías.
- Los tres cubos tienen las mismas dimensiones.
- IMAGE y NHITS contienen valores numéricos reales.
- FLAGS contiene valores enteros.
- El canal solicitado existe en los cubos.
- SPECTRAL_CHANNELS contiene una tabla con la columna WAVELENGTH.
- La tabla tiene información para el canal solicitado.
- La longitud de onda del canal es un valor escalar, numérico, finito y positivo.

Las validaciones estructurales generan ValueError con mensajes descriptivos.
El endpoint captura esos errores y devuelve HTTP 503 con un mensaje general.
El diagnóstico detallado se registra en la terminal del backend.

Se conservan las operaciones existentes sobre FLAGS, que utilizan
los bits 1 y 19.

### Estado de verificación

La consulta con el FITS real de M101 generó correctamente los tres paneles
después de agregar las validaciones.

Se ejecutó tests/test_science_preview.py con resultado de 22 pruebas
aprobadas y ninguna omitida.

Las pruebas utilizan FITS sintéticos temporales y comprueban la generación
de un PNG válido, el tipo image/png del endpoint y los errores por
extensiones ausentes, dimensiones incompatibles, canales inexistentes,
información espectral inválida, configuración ausente y archivos
inexistentes o corruptos.

Estas pruebas se ejecutan sin descargar M101 ni configurar una ruta
personal al FITS.

### Verificación de la suite completa

La ejecución del backend terminó con 68 pruebas aprobadas,
ninguna omitida y una advertencia de deprecación de Starlette TestClient.

Comando ejecutado desde `apps/science-api`:

```powershell
..\..\.venv\Scripts\python.exe -m pytest tests -v
```

## Corrección del catálogo de objetos

Se eliminó la inserción manual de M101 en `app/services/objects.py`.

El catálogo se construye a partir de `list_observations()`.
La información `science_preview` se asocia únicamente cuando existe
un objeto llamado M101 en esas observaciones, ignorando diferencias
entre mayúsculas y minúsculas.

Si M101 está ausente, el catálogo conserva únicamente los objetos
encontrados. Si está presente, conserva sus observaciones y su
identificador sin agregar una entrada duplicada.

### Verificación

- 17 pruebas del catálogo aprobadas.
- 68 pruebas aprobadas en la suite completa del backend.
- Se comprobaron M101 presente, ausente, sin duplicados y catálogo vacío.
- ESLint del Route Handler y sus pruebas completado sin errores.
- Generación de tipos de Next.js completada correctamente.
- TypeScript (`tsc --noEmit`) completado sin errores.

## Política de FLAGS para la visualización de M101

La referencia oficial utilizada es la documentación del Mosaic Tool de IRSA:

https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/mosaic.html

IRSA describe la propagación de OVERFLOW, OUTLIER y SOURCE en los
mosaicos. El encabezado FLAGS del archivo M101_irsa.fits inspeccionado
confirma MP_OVERFLOW=1, MP_OUTLIER=19 y MP_SOURCE=21.

Para la figura exploratoria de M101 se decidió excluir los píxeles
marcados con OVERFLOW o OUTLIER. Se conserva SOURCE para mostrar
las fuentes astronómicas. También se exige IMAGE finita y NHITS > 0.

La recomendación de IRSA sobre visualizar las máscaras problemáticas
respalda la identificación de esas banderas. Su exclusión de la figura
es una política de visualización del proyecto.

El parámetro bad_flag_bits del README corresponde a la fotometría
del pipeline. Para esta visualización del mosaico se utiliza el
subconjunto (1, 19). Esta política tiene alcance específico para M101.
Las banderas adicionales no se excluyen automáticamente y requieren
revisión si se admite otro producto o versión.

Las pruebas comprueban cada bandera seleccionada, sus combinaciones
con SOURCE, datos no finitos y cobertura no positiva.

### Verificación de la máscara

Se ejecutó `tests/test_science_preview.py` con 37 pruebas aprobadas,
ninguna omitida y una advertencia de deprecación de Starlette TestClient.

Las pruebas incluyen las banderas individuales, sus combinaciones,
datos no finitos, cobertura no positiva y flujo negativo finito.

### Estado de revisión

Los significados de los bits se contrastaron con la documentación
oficial de IRSA y el encabezado FLAGS del FITS local de M101.

La política implementada excluye los bits 1 y 19 para la visualización
de este mosaico. Su justificación y alcance quedan documentados para
revisión del equipo.

La suite completa del backend pasó con 83 pruebas aprobadas y una
advertencia de deprecación de Starlette TestClient.

## Proxy científico en contenedores

El Route Handler de Next.js utiliza `SCIENCE_API_URL` como dirección
base del backend, sin incluir `/api/v1`.

Para frontend y backend en la misma red de Docker Compose:

```text
SCIENCE_API_URL=http://science-api:8000
```

`science-api` es el nombre del servicio backend. La comunicación utiliza
el puerto interno 8000. Uvicorn escucha en `0.0.0.0` dentro del contenedor.

El FITS local se monta en modo de solo lectura en
`/data/M101_irsa.fits`. El backend configura:

```text
M101_FITS_PATH=/data/M101_irsa.fits
```

### Ejecutar la prueba

Desde la raíz del repositorio, con el FITS descargado en
`data/m101/M101_irsa.fits`:

```powershell
docker compose -p m101-proxy-test -f compose.proxy-test.yaml up --build -d
docker compose -p m101-proxy-test -f compose.proxy-test.yaml ps
```

Consultar el proxy en:

http://localhost:3001/api/science/m101

Detener el backend y actualizar la página:

```powershell
docker compose -p m101-proxy-test -f compose.proxy-test.yaml stop science-api
```

La respuesta esperada es HTTP 503.

Reiniciar el backend:

```powershell
docker compose -p m101-proxy-test -f compose.proxy-test.yaml start science-api
```

Cuando el backend esté saludable, actualizar la página.
La figura debe volver a cargar.

Para detener y retirar los contenedores de prueba:

```powershell
docker compose -p m101-proxy-test -f compose.proxy-test.yaml down
```

### Servidores diferentes

Configurar `SCIENCE_API_URL` con una dirección del backend accesible
desde el servidor Next.js. Por ejemplo:

```text
SCIENCE_API_URL=https://api.ejemplo.org
```

La dirección es ilustrativa. Deben comprobarse DNS, conectividad,
puertos y certificados HTTPS del despliegue real.

La variable debe estar disponible al iniciar Next.js.
`127.0.0.1` corresponde al propio entorno de red del proceso.

### Errores y tiempos de espera

El proxy aplica un timeout de diez segundos a la conexión y a la
lectura completa de la respuesta.

- 200: contenido no vacío de tipo image/png.
- 502: formato inesperado o cuerpo vacío.
- 503: configuración ausente, error de conexión o respuesta fallida
  del backend.
- 504: tiempo de espera agotado.

### Verificación realizada

- Siete pruebas automatizadas del Route Handler aprobadas.
- Timeout real durante la lectura del cuerpo comprobado.
- Figura recibida correctamente entre contenedores separados.
- Error 503 comprobado con el backend detenido.
- Recuperación comprobada después de reiniciar el backend.

El despliegue en servidores físicos o remotos diferentes queda
pendiente de verificar.

## Justificación de HTTPX y HTTPX2

Los clientes de IRSA y SIA importan `httpx`.
Se conserva `httpx==0.28.1` para esas consultas.

Starlette 1.10.0 utiliza `httpx2` en su módulo `starlette.testclient`.
Las pruebas del backend utilizan ese cliente mediante FastAPI TestClient.
Se conserva `httpx2==2.13.0` por este uso comprobado.

### Verificación en Docker

Versiones inspeccionadas:

- FastAPI 0.162.0.
- Starlette 1.10.0.
- HTTPX 0.28.1.
- HTTPX2 2.13.0.

Se confirmó que el cliente seleccionado por `starlette.testclient`
es `httpx2`.

`python -m pip check` terminó con:
`No broken requirements found.`

La suite del backend se ejecutó en un contenedor temporal sin red,
utilizando las dependencias de la imagen construida desde requirements.txt
y el proyecto montado en modo de solo lectura.

Resultado: 83 pruebas aprobadas en 3.97 segundos.