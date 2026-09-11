import { NextResponse } from "next/server";

/**
 * Step 5.3: Health Check API Route
 * Returns consistent response shape { success: true, data: { status, timestamp } }
 */
export async function GET() {
  return NextResponse.json({
    success: true,
    data: {
      status: "ok",
      service: "AgriSentinel AI & Field Gateway API",
      timestamp: new Date().toISOString(),
    },
  });
}
