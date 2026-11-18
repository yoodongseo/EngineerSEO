import { NextRequest } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export const dynamic = "force-dynamic";

async function proxyHandler(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const apiPath = path.join("/");

  // 백엔드 URL 구성 (쿼리 파라미터 포함)
  const url = new URL(`/api/${apiPath}`, BACKEND_URL);
  request.nextUrl.searchParams.forEach((value, key) => {
    url.searchParams.set(key, value);
  });

  try {
    const fetchOptions: RequestInit = {
      method: request.method,
      headers: { "Content-Type": "application/json" },
      signal: request.signal,
      cache: "no-store",
    };

    // Body가 있는 메서드 처리
    if (["POST", "PUT", "PATCH"].includes(request.method)) {
      fetchOptions.body = await request.text();
    }

    const response = await fetch(url.toString(), fetchOptions);

    // SSE 스트리밍 응답 처리
    const contentType = response.headers.get("Content-Type") || "";
    if (contentType.includes("text/event-stream")) {
      // ReadableStream으로 SSE를 클라이언트에 스트리밍 전달
      const stream = response.body;
      if (!stream) {
        return new Response("No stream available", { status: 502 });
      }

      return new Response(stream, {
        status: 200,
        headers: {
          "Content-Type": "text/event-stream",
          "Cache-Control": "no-cache",
          Connection: "keep-alive",
          "X-Accel-Buffering": "no",
        },
      });
    }

    if (response.status === 204) {
      return new Response(null, { status: 204 });
    }

    // 일반 JSON 응답
    const data = await response.text();
    return new Response(data, {
      status: response.status,
      headers: {
        "Content-Type":
          response.headers.get("Content-Type") || "application/json",
      },
    });
  } catch (error) {
    console.error(`[Proxy Error] ${request.method} /api/${apiPath}:`, error);
    return new Response(
      JSON.stringify({
        detail: `백엔드 서버에 연결할 수 없습니다 (${BACKEND_URL})`,
      }),
      { status: 502, headers: { "Content-Type": "application/json" } }
    );
  }
}

export const GET = proxyHandler;
export const POST = proxyHandler;
export const PUT = proxyHandler;
export const DELETE = proxyHandler;
export const PATCH = proxyHandler;
