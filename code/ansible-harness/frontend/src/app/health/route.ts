import { NextRequest } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function GET(_request: NextRequest) {
  try {
    const response = await fetch(`${BACKEND_URL}/health`);
    const data = await response.text();
    return new Response(data, {
      status: response.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch {
    return new Response(
      JSON.stringify({ status: "unhealthy", backend: BACKEND_URL }),
      { status: 502, headers: { "Content-Type": "application/json" } }
    );
  }
}
