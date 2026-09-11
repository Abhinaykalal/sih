import { NextRequest, NextResponse } from "next/server";
import { evaluateResilienceAlerts } from "@/lib/resilienceEngine";
import { SensorReading } from "@/lib/sensorService";

/**
 * Step 5.2: Dedicated Resilience Alerts Evaluation API Route
 */
export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const reading: SensorReading = body.reading;
    const history: SensorReading[] = body.history || [];

    if (!reading) {
      return NextResponse.json(
        { success: false, error: { code: "BAD_REQUEST", message: "Sensor reading payload missing" } },
        { status: 400 }
      );
    }

    const alerts = evaluateResilienceAlerts(reading, history);

    return NextResponse.json({
      success: true,
      data: {
        alerts,
        alertCount: alerts.length,
        evaluatedAt: Date.now(),
      },
    });
  } catch (err: any) {
    return NextResponse.json(
      { success: false, error: { code: "SERVER_ERROR", message: err.message || "Alert evaluation failed" } },
      { status: 500 }
    );
  }
}
