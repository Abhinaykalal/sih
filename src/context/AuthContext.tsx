"use client";
import React, { createContext, useContext, useState, useEffect } from "react";
import { supabase } from "@/lib/supabase";
import { useRouter } from "next/navigation";

/* ── Types ──────────────────────────────────────────────────── */
interface User {
    name: string;
    email: string;
    id: string;
    avatar_url?: string;
}

interface AuthContextType {
    user: User | null;
    login: (email: string, pass: string) => Promise<void>;
    signup: (name: string, email: string, pass: string) => Promise<void>;
    loginWithGoogle: () => Promise<void>;
    verifyPhone: (phone: string) => Promise<void>;
    loginWithPhone: (phone: string, otp: string) => Promise<void>;
    logout: () => Promise<void>;
    loading: boolean;
}

const AuthContext = createContext<AuthContextType>({} as AuthContextType);

/* ── Helper: upsert profile row ─────────────────────────────── */
async function upsertProfile(supabaseUser: {
    id: string;
    email?: string;
    user_metadata?: { full_name?: string; name?: string; avatar_url?: string };
}): Promise<User | null> {
    if (!supabaseUser) return null;

    // Try fetching existing profile first
    const { data: existing } = await supabase
        .from("profiles")
        .select("*")
        .eq("id", supabaseUser.id)
        .single();

    if (existing) {
        return {
            id: existing.id,
            name: existing.full_name || existing.email?.split("@")[0] || "Farmer",
            email: existing.email || "",
            avatar_url: existing.avatar_url,
        };
    }

    // Profile missing — upsert (handles Google OAuth users)
    const meta = supabaseUser.user_metadata ?? {};
    const fullName =
        meta.full_name || meta.name || supabaseUser.email?.split("@")[0] || "Farmer";

    const { data: created } = await supabase
        .from("profiles")
        .upsert(
            {
                id: supabaseUser.id,
                email: supabaseUser.email,
                full_name: fullName,
                avatar_url: meta.avatar_url ?? null,
            },
            { onConflict: "id" }
        )
        .select()
        .single();

    if (created) {
        return {
            id: created.id,
            name: created.full_name || "Farmer",
            email: created.email || "",
            avatar_url: created.avatar_url,
        };
    }
    return null;
}

/* ── Provider ───────────────────────────────────────────────── */
export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();

    useEffect(() => {
        /* 1. Restore existing session on page load */
        const initSession = async () => {
            try {
                const {
                    data: { session },
                    error,
                } = await supabase.auth.getSession();

                if (error) {
                    console.warn("Auth init warning:", error.message);
                    // Stale refresh token — wipe and let user re-login
                    if (
                        error.message.toLowerCase().includes("refresh") ||
                        error.status === 400 ||
                        error.status === 401
                    ) {
                        await supabase.auth.signOut({ scope: "local" });
                        setUser(null);
                    }
                } else if (session?.user) {
                    const profile = await upsertProfile(session.user);
                    if (profile) setUser(profile);
                }
            } catch (e) {
                console.error("Auth init fatal:", e);
            } finally {
                setLoading(false);
            }
        };

        initSession();

        /* 2. Listen for auth state changes (sign-in / sign-out / token refresh) */
        const {
            data: { subscription },
        } = supabase.auth.onAuthStateChange(async (event, session) => {
            if (event === "SIGNED_OUT" || (!session && event === "TOKEN_REFRESHED")) {
                setUser(null);
                setLoading(false);
                return;
            }

            if (session?.user) {
                try {
                    const profile = await upsertProfile(session.user);
                    if (profile) {
                        setUser(profile);
                        // Redirect after Google OAuth callback lands back on /login or /signup
                        if (
                            event === "SIGNED_IN" &&
                            typeof window !== "undefined"
                        ) {
                            const pathname = window.location.pathname;
                            if (pathname === "/login" || pathname === "/signup") {
                                router.push("/advisor");
                            }
                        }
                    }
                } catch (e) {
                    console.error("onAuthStateChange handler error:", e);
                } finally {
                    setLoading(false);
                }
            } else {
                setUser(null);
                setLoading(false);
            }
        });

        /* 3. Safety timeout — unfreeze "Authenticating…" after 6s */
        const safetyTimer = setTimeout(() => {
            setLoading(false);
        }, 6000);

        return () => {
            clearTimeout(safetyTimer);
            subscription.unsubscribe();
        };
    }, [router]);

    /* ── Auth methods ────────────────────────────────────────── */
    const login = async (email: string, pass: string) => {
        setLoading(true);
        const { data, error } = await supabase.auth.signInWithPassword({
            email,
            password: pass,
        });
        if (error) {
            setLoading(false);
            throw error;
        }
        if (data?.user) {
            const profile = await upsertProfile(data.user);
            if (profile) setUser(profile);
        }
        setLoading(false);
    };

    const signup = async (name: string, email: string, pass: string) => {
        setLoading(true);
        const { data, error } = await supabase.auth.signUp({
            email,
            password: pass,
            options: { data: { full_name: name } },
        });
        if (error) {
            setLoading(false);
            throw error;
        }
        if (data?.user) {
            const profile = await upsertProfile({
                ...data.user,
                user_metadata: { full_name: name },
            });
            if (profile) setUser(profile);
        }
        setLoading(false);
    };

    const loginWithGoogle = async () => {
        const origin = typeof window !== "undefined" ? window.location.origin : "";
        const { error } = await supabase.auth.signInWithOAuth({
            provider: "google",
            options: {
                redirectTo: `${origin}/advisor`,
                queryParams: {
                    access_type: "offline",
                    prompt: "consent",
                },
            },
        });
        if (error) throw error;
    };

    const verifyPhone = async (phone: string) => {
        const { error } = await supabase.auth.signInWithOtp({ phone });
        if (error) throw error;
    };

    const loginWithPhone = async (phone: string, otp: string) => {
        const { error } = await supabase.auth.verifyOtp({
            phone,
            token: otp,
            type: "sms",
        });
        if (error) throw error;
    };

    const logout = async () => {
        await supabase.auth.signOut();
        setUser(null);
        router.push("/");
    };

    return (
        <AuthContext.Provider
            value={{
                user,
                login,
                signup,
                loginWithGoogle,
                verifyPhone,
                loginWithPhone,
                logout,
                loading,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error("useAuth must be used within an AuthProvider");
    }
    return context;
};
