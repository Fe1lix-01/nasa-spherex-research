export async function GET(): Promise<Response> {
  const backend = process.env.SCIENCE_API_URL?.trim();

  if (!backend) {
    return Response.json(
      { error: "El servicio científico no está configurado" },
      { status: 503 },
    );
  }

  // El límite incluye la conexión y la lectura completa del PNG.
  const signal = AbortSignal.timeout(10000);

  try {
    const baseUrl = backend.replace(/\/+$/, "");

    const upstream = await fetch(
      `${baseUrl}/api/v1/science/m101/channel-63/preview`,
      {
        cache: "no-store",
        signal,
      },
    );

    if (!upstream.ok) {
      return Response.json(
        { error: "El backend no pudo generar la vista previa" },
        { status: 503 },
      );
    }

    const contentType = upstream.headers
      .get("content-type")
      ?.split(";")[0]
      .trim()
      .toLowerCase();

    if (contentType !== "image/png") {
      await upstream.body?.cancel();

      return Response.json(
        { error: "El backend devolvió un formato de imagen inesperado" },
        { status: 502 },
      );
    }

    // Leer todo el cuerpo permite controlar los errores de descarga
    // antes de enviar la respuesta al navegador.
    const image = await upstream.arrayBuffer();

    if (image.byteLength === 0) {
      return Response.json(
        { error: "El backend devolvió una imagen vacía" },
        { status: 502 },
      );
    }

    return new Response(image, {
      status: 200,
      headers: {
        "Content-Type": "image/png",
        "Cache-Control": "no-store",
      },
    });
  } catch {
    if (signal.aborted) {
      return Response.json(
        { error: "Se agotó el tiempo de espera del servicio científico" },
        { status: 504 },
      );
    }

    return Response.json(
      { error: "No fue posible comunicarse con el backend científico" },
      { status: 503 },
    );
  }
}