"use client";

import { useState } from "react";
import {
  Bell,
  ChevronRight,
  CloudSun,
  Droplets,
  Home,
  Leaf,
  Lightbulb,
  MapPin,
  Menu,
  MessageCircle,
  MoreHorizontal,
  Plus,
  ScanLine,
  Settings,
  Sprout,
  ThermometerSun,
  Tractor,
  TrendingUp,
  Waves,
  X,
  Zap,
} from "lucide-react";

type Tab = "home" | "fields" | "leaf" | "pump" | "alerts";

const fields = [
  { name: "Emerald Valley · Plot F5", crop: "Wheat", health: 94, area: "4.8 ha", color: "field-green" },
  { name: "Sunrise Block · Plot B2", crop: "Paddy", health: 87, area: "3.2 ha", color: "field-gold" },
];

export default function HomePage() {
  const [activeTab, setActiveTab] = useState<Tab>("home");
  const [menuOpen, setMenuOpen] = useState(false);
  const [pumpOn, setPumpOn] = useState(false);
  const [toast, setToast] = useState("");

  const showToast = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 2200);
  };

  const navItems: { id: Tab; label: string; icon: typeof Home }[] = [
    { id: "home", label: "Home", icon: Home },
    { id: "fields", label: "My Fields", icon: Leaf },
    { id: "leaf", label: "Leaf AI", icon: ScanLine },
    { id: "pump", label: "Pump", icon: Zap },
    { id: "alerts", label: "Alerts", icon: Bell },
  ];

  return (
    <main className="app-shell">
      <aside className={`sidebar ${menuOpen ? "sidebar-open" : ""}`}>
        <div className="brand">
          <div className="brand-mark"><Sprout size={21} strokeWidth={2.5} /></div>
          <div><strong>AgriSaathi</strong><span>Smart farming, simply.</span></div>
        </div>

        <nav className="side-nav" aria-label="Primary navigation">
          {navItems.map(({ id, label, icon: Icon }) => (
            <button key={id} className={`side-link ${activeTab === id ? "active" : ""}`} onClick={() => { setActiveTab(id); setMenuOpen(false); }}>
              <Icon size={19} />
              <span>{label}</span>
              {id === "alerts" && <em>2</em>}
            </button>
          ))}
        </nav>

        <div className="sidebar-grow" />
        <button className="side-link" onClick={() => showToast("Settings are ready for your next connection.")}><Settings size={19} /><span>Settings</span></button>
        <div className="sidebar-profile">
          <div className="avatar">JS</div>
          <div><strong>Jonathan S.</strong><span>Farmer account</span></div>
          <MoreHorizontal size={18} />
        </div>
      </aside>

      {menuOpen && <button className="sidebar-backdrop" aria-label="Close menu" onClick={() => setMenuOpen(false)} />}

      <section className="content">
        <header className="topbar">
          <button className="icon-button mobile-only" onClick={() => setMenuOpen(true)} aria-label="Open menu"><Menu size={21} /></button>
          <div className="location"><MapPin size={17} /><span>Emerald Valley, Punjab</span><ChevronRight size={15} /></div>
          <div className="top-actions">
            <button className="icon-button" onClick={() => showToast("You have 2 field alerts.")} aria-label="Notifications"><Bell size={19} /><i /></button>
            <button className="profile-button" onClick={() => showToast("Profile menu opened.")}><span className="avatar small">JS</span><span>Jonathan</span><ChevronRight size={15} /></button>
          </div>
        </header>

        <div className="page-wrap">
          {activeTab === "home" && (
            <>
              <section className="welcome-row">
                <div>
                  <p className="eyebrow">MONDAY · 02 SEP 2025</p>
                  <h1>Good morning, Jonathan<span>.</span></h1>
                  <p className="subhead">Your fields are looking healthy. Here&apos;s what matters today.</p>
                </div>
                <button className="primary-button" onClick={() => showToast("New field setup started.")}><Plus size={18} /> Add field</button>
              </section>

              <section className="hero-grid">
                <article className="weather-card">
                  <div className="weather-image">
                    <div className="sun"><CloudSun size={50} strokeWidth={1.5} /></div>
                    <div className="field-horizon" />
                    <div className="tractor"><Tractor size={42} /></div>
                  </div>
                  <div className="weather-info">
                    <div><span className="tiny-label">TODAY&apos;S WEATHER</span><strong>32°</strong><span>Bright &amp; sunny</span></div>
                    <div className="weather-stats"><span><Droplets size={14} /> 48%</span><span><Waves size={14} /> 12 km/h</span></div>
                  </div>
                </article>

                <article className="insight-card">
                  <div className="card-topline"><span className="ai-badge"><Lightbulb size={15} /> Saathi AI</span><span>Updated 8 min ago</span></div>
                  <h2>Water your wheat tonight.</h2>
                  <p>Soil moisture is dropping below the ideal range. A 24-minute irrigation cycle will keep Plot F5 in the optimal zone.</p>
                  <div className="insight-bottom"><div className="mini-metric"><span>Soil moisture</span><strong>31%</strong></div><button onClick={() => { setPumpOn(true); showToast("Pump scheduled for tonight."); }}>Schedule irrigation <ChevronRight size={16} /></button></div>
                </article>
              </section>

              <section className="section-head"><div><p className="eyebrow">LIVE TELEMETRY</p><h2>Field conditions</h2></div><button className="text-button" onClick={() => setActiveTab("fields")}>View details <ChevronRight size={16} /></button></section>
              <section className="metrics-grid">
                <Metric icon={<Droplets />} label="Soil moisture" value="31" unit="%" trend="+4% today" positive />
                <Metric icon={<ThermometerSun />} label="Soil temperature" value="24.8" unit="°C" trend="Ideal range" positive />
                <Metric icon={<Waves />} label="Water tank" value="68" unit="%" trend="1,240 L remaining" positive />
                <Metric icon={<Zap />} label="Pump status" value={pumpOn ? "ON" : "OFF"} unit="" trend={pumpOn ? "Scheduled cycle" : "Ready to run"} positive={pumpOn} />
              </section>

              <section className="section-head fields-head"><div><p className="eyebrow">YOUR LAND</p><h2>My fields</h2></div><button className="round-button" onClick={() => showToast("Map view opened.")}><MapPin size={18} /></button></section>
              <section className="fields-grid">
                {fields.map((field, index) => <FieldCard key={field.name} {...field} index={index} onOpen={() => showToast(`${field.name} selected.`)} />)}
              </section>

              <section className="bottom-cta">
                <div className="cta-icon"><MessageCircle size={22} /></div>
                <div><strong>Need a second opinion?</strong><span>Ask Saathi about your crop, soil or next decision.</span></div>
                <button onClick={() => showToast("AI assistant opened.")}>Ask Saathi <ChevronRight size={17} /></button>
              </section>
            </>
          )}

          {activeTab === "fields" && <FieldsView onToast={showToast} />}
          {activeTab === "leaf" && <LeafView onToast={showToast} />}
          {activeTab === "pump" && <PumpView pumpOn={pumpOn} setPumpOn={setPumpOn} onToast={showToast} />}
          {activeTab === "alerts" && <AlertsView onToast={showToast} />}
        </div>

        <nav className="bottom-nav" aria-label="Mobile navigation">
          {navItems.map(({ id, label, icon: Icon }) => <button key={id} className={activeTab === id ? "active" : ""} onClick={() => setActiveTab(id)}><Icon size={20} /><span>{label}</span>{id === "alerts" && <b>2</b>}</button>)}
        </nav>
      </section>

      {toast && <div className="toast"><span>✓</span>{toast}</div>}
    </main>
  );
}

function Metric({ icon, label, value, unit, trend, positive }: { icon: React.ReactNode; label: string; value: string; unit: string; trend: string; positive: boolean }) {
  return <article className="metric-card"><div className="metric-icon">{icon}</div><span className="metric-label">{label}</span><div className="metric-value">{value}<small>{unit}</small></div><span className={`metric-trend ${positive ? "positive" : ""}`}><TrendingUp size={13} /> {trend}</span></article>;
}

function FieldCard({ name, crop, health, area, color, index, onOpen }: { name: string; crop: string; health: number; area: string; color: string; index: number; onOpen: () => void }) {
  return <button className="field-card" onClick={onOpen}><div className={`field-art ${color}`}><div className="crop-lines">{Array.from({ length: 8 }).map((_, i) => <span key={i} style={{ transform: `rotate(${i % 2 ? -3 : 3}deg)` }} />)}</div><div className="field-pill">{crop}</div><div className="health"><Leaf size={13} /> {health}%</div></div><div className="field-copy"><div><strong>{name}</strong><span>{area} · Sensor online</span></div><ChevronRight size={19} /></div></button>;
}

function FieldsView({ onToast }: { onToast: (s: string) => void }) {
  return <ViewFrame eyebrow="YOUR LAND" title="My fields" subtitle="Monitor every plot from one calm view."><div className="fields-grid large">{fields.map((f, i) => <FieldCard key={f.name} {...f} index={i} onOpen={() => onToast(`${f.name} selected.`)} />)}<button className="add-field-card" onClick={() => onToast("New field setup started.")}><Plus size={28} /><strong>Add a new field</strong><span>Connect a location and sensors</span></button></div></ViewFrame>;
}

function LeafView({ onToast }: { onToast: (s: string) => void }) {
  return <ViewFrame eyebrow="COMPUTER VISION" title="Leaf AI" subtitle="Check crop health with a photo. Saathi will highlight what needs attention."><div className="scan-panel"><div className="scan-visual"><div className="scan-corners" /><ScanLine size={58} strokeWidth={1.3} /><strong>Scan a leaf</strong><span>Upload a clear photo of the affected area</span></div><div className="scan-actions"><button className="primary-button" onClick={() => onToast("Camera upload opened.")}><ScanLine size={18} /> Scan crop</button><button className="secondary-button" onClick={() => onToast("Example analysis opened.")}>See example</button></div></div></ViewFrame>;
}

function PumpView({ pumpOn, setPumpOn, onToast }: { pumpOn: boolean; setPumpOn: (v: boolean) => void; onToast: (s: string) => void }) {
  return <ViewFrame eyebrow="IRRIGATION" title="Pump control" subtitle="Control connected irrigation equipment and keep an eye on usage."><div className="pump-panel"><div className="pump-status"><div className={`power-orb ${pumpOn ? "on" : ""}`}><Zap size={34} /></div><div><span className="tiny-label">PLOT F5 · MAIN PUMP</span><h3>{pumpOn ? "Running now" : "Ready to run"}</h3><p>{pumpOn ? "Water cycle is active." : "No active irrigation cycle."}</p></div><button className={`toggle ${pumpOn ? "on" : ""}`} onClick={() => { const next = !pumpOn; setPumpOn(next); onToast(next ? "Pump turned on." : "Pump turned off."); }}><span /></button></div><div className="pump-details"><span><strong>24 min</strong> recommended cycle</span><span><strong>18 L/min</strong> flow rate</span><span><strong>68%</strong> tank level</span></div></div></ViewFrame>;
}

function AlertsView({ onToast }: { onToast: (s: string) => void }) {
  const alerts = [{ title: "Soil moisture is low", body: "Plot F5 has reached 31%. Consider irrigation tonight.", time: "8 min ago", icon: <Droplets /> }, { title: "Paddy looks healthy", body: "No signs of disease detected in Sunrise Block.", time: "2 hr ago", icon: <Leaf /> }];
  return <ViewFrame eyebrow="ATTENTION" title="Field alerts" subtitle="Important changes are kept here so nothing gets missed."><div className="alerts-list">{alerts.map((a, i) => <button className={`alert-row ${i === 0 ? "unread" : ""}`} key={a.title} onClick={() => onToast("Alert marked as reviewed.")}><div className="alert-icon">{a.icon}</div><div><strong>{a.title}</strong><p>{a.body}</p><span>{a.time}</span></div><ChevronRight size={18} /></button>)}</div></ViewFrame>;
}

function ViewFrame({ eyebrow, title, subtitle, children }: { eyebrow: string; title: string; subtitle: string; children: React.ReactNode }) {
  return <div className="view-frame"><div className="view-heading"><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p>{subtitle}</p></div>{children}</div>;
}
