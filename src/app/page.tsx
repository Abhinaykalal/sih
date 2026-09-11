export default function Home() {
    return (
        <main style={{ minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "2rem", textAlign: "center" }}>
            <div style={{ maxWidth: "600px", background: "#FFFFFF", padding: "2.5rem", borderRadius: "20px", boxShadow: "0 10px 30px rgba(18, 61, 37, 0.06)", border: "1px solid #EAF8E8" }}>
                <div style={{ display: "inline-flex", padding: "0.5rem 1rem", background: "#EAF8E8", borderRadius: "999px", color: "#2E8B36", fontSize: "0.875rem", fontWeight: 600, marginBottom: "1.25rem" }}>
                    🌱 AgriSaathi AI Platform
                </div>
                <h1 style={{ fontSize: "1.75rem", fontWeight: 700, color: "#123D25", margin: "0 0 1rem 0" }}>
                    Android Mobile Platform Active
                </h1>
                <p style={{ color: "#6B7C70", lineHeight: 1.6, margin: "0 0 1.5rem 0", fontSize: "1rem" }}>
                    The native Android application under <code>android-app/</code> is active. Core API services and IoT telemetry engines are operational on port 8000.
                </p>
                <div style={{ display: "flex", justifyContent: "center", gap: "1rem", flexWrap: "wrap" }}>
                    <span style={{ padding: "0.5rem 1rem", background: "#F5FBF1", borderRadius: "12px", border: "1px solid #EAF8E8", fontSize: "0.85rem", color: "#123D25", fontWeight: 500 }}>
                        📡 FastAPI Backend: <b>8000</b>
                    </span>
                    <span style={{ padding: "0.5rem 1rem", background: "#F5FBF1", borderRadius: "12px", border: "1px solid #EAF8E8", fontSize: "0.85rem", color: "#123D25", fontWeight: 500 }}>
                        📱 Android App: <b>android-app/</b>
                    </span>
                </div>
            </div>
        </main>
    );
}
