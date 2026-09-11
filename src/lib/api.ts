import { supabase } from './supabase';

const ML_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export class AuthenticationError extends Error {
    constructor(message: string = "Authentication required. Please login to access AI modules.") {
        super(message);
        this.name = "AuthenticationError";
    }
}

/**
 * Authenticated API wrapper
 * Checks if user is logged in before making backend API calls
 */
export async function authenticatedFetch(
    endpoint: string,
    options?: RequestInit
): Promise<Response> {
    // Check if user is authenticated
    const { data: { session } } = await supabase.auth.getSession();

    if (!session || !session.user) {
        throw new AuthenticationError();
    }

    // Make the API call
    const url = `${ML_BASE}${endpoint}`;
    return fetch(url, options);
}

/**
 * Helper for POST requests with JSON body
 */
export async function authenticatedPost(
    endpoint: string,
    body: Record<string, unknown>
): Promise<Response> {
    return authenticatedFetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
}

/**
 * Helper for GET requests with query params
 */
export async function authenticatedGet(
    endpoint: string,
    params?: Record<string, string>
): Promise<Response> {
    const url = params
        ? `${endpoint}?${new URLSearchParams(params).toString()}`
        : endpoint;
    return authenticatedFetch(url);
}
