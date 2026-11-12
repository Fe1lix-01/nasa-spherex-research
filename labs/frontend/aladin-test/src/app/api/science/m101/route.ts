const BACKEND = process.env.SCIENCE_API_URL ?? "http://127.0.0.1:8000";

export async function GET(): Promise<Response> {
  try {
    const upstream = await fetch(`${BACKEND}/api/v1/science/m101/channel-63/preview`, {
      cache: "no-store",
      signal: AbortSignal.timeout(10000),
    });
    if (!upstream.ok || !upstream.body) {
      return Response.json({ error: "Vista previa no disponible" }, { status: 503 });
    }
    return new Response(upstream.body, {
      headers: { "Content-Type": "image/png", "Cache-Control": "no-store" },
    });
  } catch {
    return Response.json({ error: "Backend no disponible" }, { status: 503 });
  }
}
