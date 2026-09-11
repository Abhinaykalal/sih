import { NextRequest, NextResponse } from "next/server";
import { fetchSensorData } from "@/lib/sensorService";

/**
 * Step 5.1: Next.js Server Proxy Route for ESP32 Sensor Fetching
 * Avoids CORS errors by proxying HTTP GET requests server-side.
 */
export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ esp32Ip: string }> }
) {
  try {
    const { esp32Ip } = await params;
    if (!esp32Ip) {
      return NextResponse.json(
        { success: false, error: { code: "BAD_REQUEST", message: "ESP32 IP parameter missing" } },
        { status: 400 }
      );
    }

    const result = await fetchSensorData(esp32Ip, 1);

    if (result.success) {
      return NextResponse.json({
        success: true,
        data: result.data,
      });
    } else {
      return NextResponse.json(
        {
          success: false,
          error: result.error,
        },
        { status: 504 }
      );
    }
  } catch (err: any) {
    return NextResponse.json(
      {
        success: false,
        error: { code: "SERVER_ERROR", message: err.message || "Failed to proxy ESP32 request" },
      },
      { status: 500 }
    );
  }
}
