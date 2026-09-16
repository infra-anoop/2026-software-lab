import type { NextRequest } from "next/server";

export const runtime = "nodejs";

function workerBaseUrl(): string {
  const raw = process.env.SMART_WRITER_V2_WORKER_URL ?? "http://127.0.0.1:8080";
  return raw.replace(/\/$/, "");
}

function auditSecret(): string | undefined {
  const value = process.env.SMART_WRITER_V2_AUDIT_SECRET;
  return value && value.trim().length > 0 ? value : undefined;
}

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
): Promise<Response> {
  const secret = auditSecret();
  if (secret === undefined) {
    return Response.json(
      { detail: "SMART_WRITER_V2_AUDIT_SECRET is not configured" },
      { status: 503 },
    );
  }

  const { path } = await context.params;
  const suffix = path.join("/");
  const dest = new URL(`${workerBaseUrl()}/${suffix}`);
  dest.search = request.nextUrl.search;

  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.set("X-Audit-Secret", secret);

  const method = request.method.toUpperCase();
  const body =
    method === "GET" || method === "HEAD" ? undefined : await request.arrayBuffer();

  const upstream = await fetch(dest, {
    method,
    headers,
    body,
    redirect: "manual",
  });

  const outHeaders = new Headers(upstream.headers);
  return new Response(upstream.body, {
    status: upstream.status,
    headers: outHeaders,
  });
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
): Promise<Response> {
  return proxy(request, context);
}

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
): Promise<Response> {
  return proxy(request, context);
}

export async function PUT(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
): Promise<Response> {
  return proxy(request, context);
}

export async function PATCH(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
): Promise<Response> {
  return proxy(request, context);
}

export async function DELETE(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
): Promise<Response> {
  return proxy(request, context);
}
