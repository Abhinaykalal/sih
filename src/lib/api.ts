import { supabase } from './supabase';

const ML_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const DEVICE_ID = process.env.NEXT_PUBLIC_DEVICE_ID || "esp32-001";

export class AuthenticationError extends Error {
    constructor(message: string = "Authentication required. Please login to access AI modules.") {
        super(message);
        this.name = "AuthenticationError";
    }
}

export async function authenticatedFetch(endpoint: string, options?: RequestInit): Promise<Response> {
    const { data: { session } } = await supabase.auth.getSession();
    if (!session || !session.user) throw new AuthenticationError();
    const url = `${ML_BASE}${endpoint}`;
    return fetch(url, options);
}

export async function authenticatedPost(endpoint: string, body: Record<string, unknown>): Promise<Response> {
    return authenticatedFetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
}

export async function authenticatedGet(endpoint: string, params?: Record<string, string>): Promise<Response> {
    const url = params ? `${endpoint}?${new URLSearchParams(params).toString()}` : endpoint;
    return authenticatedFetch(url);
}

export type Telemetry = {
    soil_moisture?: number;
    soil_temperature?: number;
    temperature?: number;
    humidity?: number;
    ph?: number;
    N?: number;
    P?: number;
    K?: number;
    water_level?: number;
    [key: string]: unknown;
};

export type ApiAlert = {
    id?: string | number;
    title?: string;
    message?: string;
    body?: string;
    severity?: string;
    created_at?: string;
    read?: boolean;
    [key: string]: unknown;
};

async function apiJson<T>(endpoint: string, init?: RequestInit): Promise<T> {
    const response = await authenticatedFetch(endpoint, {
        ...init,
        headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    });
    if (!response.ok) throw new Error(`API ${response.status}`);
    return response.json() as Promise<T>;
}

function unwrap<T>(raw: unknown): T {
    if (raw && typeof raw === "object" && "data" in raw) return (raw as { data: T }).data;
    return raw as T;
}

export async function getTelemetry(): Promise<Telemetry> {
    return unwrap<Telemetry>(await apiJson(`/api/sensor/telemetry/${encodeURIComponent(DEVICE_ID)}`));
}

export async function getPumpState(): Promise<Record<string, unknown>> {
    return unwrap<Record<string, unknown>>(await apiJson(`/api/pump/state/${encodeURIComponent(DEVICE_ID)}`));
}

export async function getAlerts(): Promise<ApiAlert[]> {
    const raw = unwrap<unknown>(await apiJson("/api/notifications/"));
    return Array.isArray(raw) ? raw as ApiAlert[] : [];
}

export async function sendPumpCommand(command: "ON" | "OFF") {
    return apiJson<Record<string, unknown>>("/api/pump/command", {
        method: "POST",
        body: JSON.stringify({ device_id: DEVICE_ID, command, confirmed: true }),
    });
}

export async function checkApiHealth() {
    const response = await fetch(`${ML_BASE}/health`, { cache: "no-store" });
    if (!response.ok) throw new Error(`Health ${response.status}`);
    return response.json() as Promise<{ status?: string }>;
}

export { ML_BASE, DEVICE_ID };
