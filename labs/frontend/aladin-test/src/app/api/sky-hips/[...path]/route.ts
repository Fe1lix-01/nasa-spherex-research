// Endpoint específico para AllWISE. No acepta URLs externas del cliente.
const UPSTREAM =
  "https://irsa.ipac.caltech.edu/data/hips/CDS/AllWISE/RGB-W4-W2-W1/";

type Context = { params: Promise<{ path: string[] }> };

function isAllowed(path: string): boolean {
  if (path === "properties" || path === "Moc.fits") return true;
  if (/^Norder[0-8]\/Allsky\.jpg$/.test(path)) return true;
  const tile = /^Norder([0-8])\/Dir(\d{1,7})\/Npix(\d{1,7})\.jpg$/.exec(path);
  if (!tile) return false;
  const [, order, directory, pixel] = tile;
  const index = Number(pixel);
  return index < 12 * 4 ** Number(order)
    && Number(directory) === Math.floor(index / 10000) * 10000;
}

function errorResponse(error: string, status: number): Response {
  return Response.json({ error }, {
    status,
    headers: { "Cache-Control": "no-store" },
  });
}

export async function GET(request: Request, { params }: Context): Promise<Response> {
  const { path } = await params;
  const resource = path.join("/");
  if (!isAllowed(resource)) return errorResponse("Recurso HiPS no permitido.", 400);

  const timeout = AbortSignal.timeout(20000);
  try {
    const response = await fetch(new URL(resource, UPSTREAM), {
      // CORS lo aplica el navegador, no esta solicitud desde el servidor.
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.any([timeout, request.signal]),
    });
    if (!response.ok) {
      return errorResponse(
        `IRSA respondió HTTP ${response.status} al solicitar ${resource}.`,
        response.status === 404 ? 404 : 502,
      );
    }
    // Leer antes de responder permite capturar también un timeout del cuerpo.
    // Las imágenes se mantienen como bytes, sin convertirlas a texto/JSON.
    const body = await response.arrayBuffer();
    return new Response(body, {
      headers: {
        "Content-Type": resource === "properties"
          ? "text/plain; charset=utf-8"
          : resource.endsWith(".fits") ? "application/fits" : "image/jpeg",
        "Cache-Control": "public, max-age=3600",
        "X-Content-Type-Options": "nosniff",
      },
    });
  } catch {
    return errorResponse(
      timeout.aborted
        ? "IRSA no respondió en 20 segundos. Comprueba la conexión del servidor de Next.js."
        : "El servidor de Next.js no pudo descargar el recurso de IRSA. Comprueba su conexión a internet.",
      timeout.aborted ? 504 : 502,
    );
  }
}
