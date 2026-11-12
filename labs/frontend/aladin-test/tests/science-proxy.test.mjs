import assert from "node:assert/strict";
import { createServer } from "node:http";
import { afterEach, test } from "node:test";

import { GET } from "../src/app/api/science/m101/route.ts";

const originalBackend = process.env.SCIENCE_API_URL;

// PNG pequeño utilizado únicamente en las pruebas.
const png = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aXioAAAAASUVORK5CYII=",
  "base64",
);

afterEach(() => {
  if (originalBackend === undefined) {
    delete process.env.SCIENCE_API_URL;
  } else {
    process.env.SCIENCE_API_URL = originalBackend;
  }
});

async function conBackend(handler, comprobar) {
  const server = createServer(handler);

  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });

  const address = server.address();
  const url = `http://127.0.0.1:${address.port}`;

  process.env.SCIENCE_API_URL = url;

  try {
    await comprobar(server, url);
  } finally {
    const cerrado = new Promise((resolve, reject) => {
      server.close((error) => {
        if (error) reject(error);
        else resolve();
      });
    });

    server.closeAllConnections();
    await cerrado;
  }
}

test("devuelve 503 cuando falta SCIENCE_API_URL", async () => {
  delete process.env.SCIENCE_API_URL;

  const response = await GET();

  assert.equal(response.status, 503);
  assert.deepEqual(await response.json(), {
    error: "El servicio científico no está configurado",
  });
});

test("devuelve el PNG recibido del backend", async () => {
  await conBackend(
    (request, response) => {
      assert.equal(
        request.url,
        "/api/v1/science/m101/channel-63/preview",
      );

      response.writeHead(200, { "Content-Type": "image/png" });
      response.end(png);
    },
    async () => {
      const response = await GET();

      assert.equal(response.status, 200);
      assert.equal(response.headers.get("content-type"), "image/png");
      assert.equal(response.headers.get("cache-control"), "no-store");

      const content = Buffer.from(await response.arrayBuffer());
      assert.deepEqual(content, png);
    },
  );
});

test("devuelve 503 si el backend responde con error", async () => {
  await conBackend(
    (_request, response) => {
      response.writeHead(500, { "Content-Type": "text/plain" });
      response.end("Detalle interno del backend");
    },
    async () => {
      const response = await GET();

      assert.equal(response.status, 503);
      assert.deepEqual(await response.json(), {
        error: "El backend no pudo generar la vista previa",
      });
    },
  );
});

test("devuelve 502 si el backend responde con otro formato", async () => {
  await conBackend(
    (_request, response) => {
      response.writeHead(200, { "Content-Type": "text/html" });
      response.end("<html>Error</html>");
    },
    async () => {
      const response = await GET();

      assert.equal(response.status, 502);
      assert.deepEqual(await response.json(), {
        error: "El backend devolvió un formato de imagen inesperado",
      });
    },
  );
});

test("devuelve 502 si el PNG recibido está vacío", async () => {
  await conBackend(
    (_request, response) => {
      response.writeHead(200, { "Content-Type": "image/png" });
      response.end();
    },
    async () => {
      const response = await GET();

      assert.equal(response.status, 502);
      assert.deepEqual(await response.json(), {
        error: "El backend devolvió una imagen vacía",
      });
    },
  );
});

test("devuelve 503 ante una conexión rechazada", async () => {
  // El puerto cero solicita al sistema un puerto libre.
  const server = createServer();

  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });

  const port = server.address().port;

  await new Promise((resolve, reject) => {
    server.close((error) => {
      if (error) reject(error);
      else resolve();
    });
  });

  process.env.SCIENCE_API_URL = `http://127.0.0.1:${port}`;

  const response = await GET();

  assert.equal(response.status, 503);
  assert.deepEqual(await response.json(), {
    error: "No fue posible comunicarse con el backend científico",
  });
});

test(
  "devuelve 504 si la descarga del cuerpo supera el timeout",
  { timeout: 15000 },
  async () => {
    await conBackend(
      (_request, response) => {
        response.writeHead(200, { "Content-Type": "image/png" });
        response.flushHeaders();
        response.write(png.subarray(0, 8));

        // La respuesta queda incompleta para activar el timeout real.
      },
      async () => {
        const response = await GET();

        assert.equal(response.status, 504);
        assert.deepEqual(await response.json(), {
          error: "Se agotó el tiempo de espera del servicio científico",
        });
      },
    );
  },
);