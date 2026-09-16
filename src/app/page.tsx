"use client";

import { useEffect, useState } from "react";
import { Bell, ChevronRight, CloudSun, Droplets, Home, Leaf, Lightbulb, MapPin, Menu, MessageCircle, MoreHorizontal, Plus, Settings, Sprout, ThermometerSun, Tractor, TrendingUp, Waves, Zap } from "lucide-react";
import { getAlerts, getPumpState, getTelemetry, sendPumpCommand, type ApiAlert, type Telemetry } from "@/lib/api";

type Tab = "home" | "fields" | "pump" | "alerts";

const fields = [
  { name: "Emerald Valley · Plot F5", crop: "Wheat", health: 94, area: "4.8 ha", color: "field-green" },
  { name: "Sunrise Block · Plot B2", crop: "Paddy", health: 87, area: "3.2 ha", color: "field-gold" },
];

const num = (value: unknown, fallback: number) => typeof value === "number" && Number.isFinite(value) ? value : fallback;

export default function HomePage() {
  const [activeTab, setActiveTab] = useState<Tab>("home");
  const [menuOpen, setMenuOpen] = useState(false);
  const [pumpOn, setPumpOn] = useState(false);
  const [toast, setToast] = useState("");
  const [telemetry, setTelemetry] = useState<Telemetry>({});
  const [alerts, setAlerts] = useState<ApiAlert[]>([]);
  const [live, setLive] = useState(false);
  const [loadingPump, setLoadingPump] = useState(false);

  const showToast = (message: string) => { setToast(message); window.setTimeout(() => setToast(""), 2200); };

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      const [sensor, pump, notificationList] = await Promise.allSettled([getTelemetry(), getPumpState(), getAlerts()]);
      if (!mounted) return;
      if (sensor.status === "fulfilled") { setTelemetry(sensor.value); setLive(true); } else setLive(false);
      if (pump.status === "fulfilled") {
        const value = pump.value;
        const state = value.state ?? value.status ?? value.pump_state ?? value.is_on;
        setPumpOn(state === true || state === "ON" || state === "on" || state === "running" || state === "RUNNING");
      }
      if (notificationList.status === "fulfilled") setAlerts(notificationList.value);
    };
    load();
    const timer = window.setInterval(load, 30000);
    return () => { mounted = false; window.clearInterval(timer); };
  }, []);

  const moisture = num(telemetry.soil_moisture, 31);
  const soilTemp = num(telemetry.soil_temperature ?? telemetry.temperature, 24.8);
  const humidity = num(telemetry.humidity, 48);
  const water = num(telemetry.water_level, 68);
  const unreadAlerts = alerts.filter((a) => !a.read).length || Math.min(alerts.length, 2);
  const navItems: { id: Tab; label: string; icon: typeof Home }[] = [
    { id: "home", label: "Home", icon: Home },
    { id: "fields", label: "My Fields", icon: Leaf },
    { id: "pump", label: "Pump", icon: Zap },
    { id: "alerts", label: "Alerts", icon: Bell },
  ];

  const togglePump = async (next: boolean) => {
    if (loadingPump) return;
    setLoadingPump(true);
    try { await sendPumpCommand(next ? "ON" : "OFF"); setPumpOn(next); showToast(next ? "Pump command sent." : "Pump stop command sent."); }
    catch { showToast("Pump command failed. Check the backend connection."); }
    finally { setLoadingPump(false); }
  };

  return <main className="app-shell">
    <aside className={`sidebar ${menuOpen ? "sidebar-open" : ""}`}>
      <div className="brand"><div className="brand-mark"><Sprout size={21} strokeWidth={2.5} /></div><div><strong>AgriSaathi</strong><span>Smart farming, simply.</span></div></div>
      <nav className="side-nav" aria-label="Primary navigation">
        {navItems.map(({ id, label, icon: Icon }) => <button key={id} className={`side-link ${activeTab === id ? "active" : ""}`} onClick={() => { setActiveTab(id); setMenuOpen(false); }}><Icon size={19} /><span>{label}</span>{id === "alerts" && unreadAlerts > 0 && <em>{unreadAlerts}</em>}</button>)}
      </nav>
      <div className="sidebar-grow" />
      <button className="side-link" onClick={() => showToast("Settings opened.")}><Settings size={19} /><span>Settings</span></button>
      <div className="sidebar-profile"><div className="avatar">JS</div><div><strong>Jonathan S.</strong><span>Farmer account</span></div><MoreHorizontal size={18} /></div>
    </aside>
    {menuOpen && <button className="sidebar-backdrop" aria-label="Close menu" onClick={() => setMenuOpen(false)} />}
    <section className="content">
      <header className="topbar"><button className="icon-button mobile-only" onClick={() => setMenuOpen(true)} aria-label="Open menu"><Menu size={21} /></button><div className="location"><MapPin size={17} /><span>Emerald Valley, Punjab</span><ChevronRight size={15} /></div><div className="top-actions"><button className="icon-button" onClick={() => setActiveTab("alerts")} aria-label="Notifications"><Bell size={19} />{unreadAlerts > 0 && <i />}</button><button className="profile-button" onClick={() => showToast("Profile menu opened.")}><span className="avatar small">JS</span><span>Jonathan</span><ChevronRight size={15} /></button></div></header>
      <div className="page-wrap">
        {activeTab === "home" && <HomeView live={live} moisture={moisture} soilTemp={soilTemp} humidity={humidity} water={water} pumpOn={pumpOn} setActiveTab={setActiveTab} showToast={showToast} />}
        {activeTab === "fields" && <FieldsView onToast={showToast} />}
        {activeTab === "pump" && <PumpView pumpOn={pumpOn} onToggle={togglePump} loading={loadingPump} />}
        {activeTab === "alerts" && <AlertsView alerts={alerts} onToast={showToast} />}
      </div>
      <nav className="bottom-nav" aria-label="Mobile navigation">{navItems.map(({ id, label, icon: Icon }) => <button key={id} className={activeTab === id ? "active" : ""} onClick={() => setActiveTab(id)}><Icon size={20} /><span>{label}</span>{id === "alerts" && unreadAlerts > 0 && <b>{unreadAlerts}</b>}</button>)}</nav>
    </section>
    {toast && <div className="toast"><span>✓</span>{toast}</div>}
  </main>;
}

function HomeView({ live, moisture, soilTemp, humidity, water, pumpOn, setActiveTab, showToast }: { live: boolean; moisture: number; soilTemp: number; humidity: number; water: number; pumpOn: boolean; setActiveTab: (tab: Tab) => void; showToast: (s: string) => void }) {
  return <>
    <section className="welcome-row"><div><p className="eyebrow">LIVE FARM DASHBOARD</p><h1>Good morning, Jonathan<span>.</span></h1><p className="subhead">Your fields are connected. Here&apos;s what matters today.</p></div><div className="welcome-actions"><span className={`connection-badge ${live ? "online" : "offline"}`}><span />{live ? "Live data" : "Demo data"}</span><button className="primary-button" onClick={() => showToast("New field setup started.")}><Plus size={18} /> Add field</button></div></section>
    <section className="hero-grid"><article className="weather-card"><div className="weather-image"><div className="sun"><CloudSun size={50} strokeWidth={1.5} /></div><div className="field-horizon" /><div className="tractor"><Tractor size={42} /></div></div><div className="weather-info"><div><span className="tiny-label">FIELD CONDITIONS</span><strong>{Math.round(32)}°</strong><span>{live ? "Live sensor environment" : "Weather preview"}</span></div><div className="weather-stats"><span><Droplets size={14} /> {Math.round(humidity)}% humidity</span><span><Waves size={14} /> {live ? "Sensor online" : "12 km/h wind"}</span></div></div></article><article className="insight-card"><div className="card-topline"><span className="ai-badge"><Lightbulb size={15} /> Saathi AI</span><span>{live ? "Based on live telemetry" : "Preview insight"}</span></div><h2>{moisture < 35 ? "Water your wheat tonight." : "Your wheat is in a good moisture range."}</h2><p>{moisture < 35 ? `Soil moisture is ${Math.round(moisture)}%. A controlled irrigation cycle can move Plot F5 toward its target range.` : `Soil moisture is ${Math.round(moisture)}%. Keep monitoring the field and follow the next recommended action.`}</p><div className="insight-bottom"><div className="mini-metric"><span>Soil moisture</span><strong>{Math.round(moisture)}%</strong></div><button onClick={() => setActiveTab("pump")}>Review irrigation <ChevronRight size={16} /></button></div></article></section>
    <section className="section-head"><div><p className="eyebrow">LIVE TELEMETRY</p><h2>Field conditions</h2></div><button className="text-button" onClick={() => setActiveTab("fields")}>View details <ChevronRight size={16} /></button></section>
    <section className="metrics-grid"><Metric icon={<Droplets />} label="Soil moisture" value={Math.round(moisture).toString()} unit="%" trend={live ? "Live sensor" : "Demo value"} positive={moisture >= 25} /><Metric icon={<ThermometerSun />} label="Soil temperature" value={soilTemp.toFixed(1)} unit="°C" trend={live ? "Live sensor" : "Demo value"} positive /><Metric icon={<Waves />} label="Water tank" value={Math.round(water).toString()} unit="%" trend={water > 25 ? "Healthy reserve" : "Low reserve"} positive={water > 25} /><Metric icon={<Zap />} label="Pump status" value={pumpOn ? "ON" : "OFF"} unit="" trend={pumpOn ? "Active" : "Ready"} positive={pumpOn} /></section>
    <section className="section-head fields-head"><div><p className="eyebrow">YOUR LAND</p><h2>My fields</h2></div><button className="round-button" onClick={() => setActiveTab("fields")}><MapPin size={18} /></button></section>
    <section className="fields-grid">{fields.map((field, index) => <FieldCard key={field.name} {...field} index={index} onOpen={() => showToast(`${field.name} selected.`)} />)}</section>
    <section className="bottom-cta"><div className="cta-icon"><MessageCircle size={22} /></div><div><strong>Need a second opinion?</strong><span>Ask Saathi about your crop, soil or next decision.</span></div><button onClick={() => showToast("Saathi assistant opened.")}>Ask Saathi <ChevronRight size={17} /></button></section>
  </>;
}

function Metric({ icon, label, value, unit, trend, positive }: { icon: React.ReactNode; label: string; value: string; unit: string; trend: string; positive: boolean }) { return <article className="metric-card"><div className="metric-icon">{icon}</div><span className="metric-label">{label}</span><div className="metric-value">{value}<small>{unit}</small></div><span className={`metric-trend ${positive ? "positive" : ""}`}><TrendingUp size={13} /> {trend}</span></article>; }
function FieldCard({ name, crop, health, area, color, index, onOpen }: { name: string; crop: string; health: number; area: string; color: string; index: number; onOpen: () => void }) { return <button className="field-card" onClick={onOpen}><div className={`field-art ${color}`}><div className="crop-lines">{Array.from({ length: 8 }).map((_, i) => <span key={i} style={{ transform: `rotate(${i % 2 ? -3 : 3}deg)` }} />)}</div><div className="field-pill">{crop}</div><div className="health"><Leaf size={13} /> {health}%</div></div><div className="field-copy"><div><strong>{name}</strong><span>{area} · Sensor online</span></div><ChevronRight size={19} /></div></button>; }
function FieldsView({ onToast }: { onToast: (s: string) => void }) { return <ViewFrame eyebrow="YOUR LAND" title="My fields" subtitle="Monitor every plot from one calm view."><div className="fields-grid large">{fields.map((f, i) => <FieldCard key={f.name} {...f} index={i} onOpen={() => onToast(`${f.name} selected.`)} />)}<button className="add-field-card" onClick={() => onToast("New field setup started.")}><Plus size={28} /><strong>Add a new field</strong><span>Connect a location and sensors</span></button></div></ViewFrame>; }
function PumpView({ pumpOn, onToggle, loading }: { pumpOn: boolean; onToggle: (v: boolean) => void; loading: boolean }) { return <ViewFrame eyebrow="IRRIGATION" title="Pump control" subtitle="Control connected irrigation equipment and keep an eye on usage."><div className="pump-panel"><div className="pump-status"><div className={`power-orb ${pumpOn ? "on" : ""}`}><Zap size={34} /></div><div><span className="tiny-label">PLOT F5 · MAIN PUMP</span><h3>{pumpOn ? "Running now" : "Ready to run"}</h3><p>{pumpOn ? "Command acknowledged by the dashboard." : "No active irrigation cycle."}</p></div><button disabled={loading} aria-label="Toggle pump" className={`toggle ${pumpOn ? "on" : ""}`} onClick={() => onToggle(!pumpOn)}><span /></button></div><div className="pump-details"><span><strong>24 min</strong> recommended cycle</span><span><strong>18 L/min</strong> flow rate</span><span><strong>68%</strong> tank level</span></div><p className="safety-note">Pump commands are sent through the backend safety controller. Always verify the field is safe before actuation.</p></div></ViewFrame>; }
function AlertsView({ alerts, onToast }: { alerts: ApiAlert[]; onToast: (s: string) => void }) { const items = alerts.length ? alerts.slice(0, 8).map((a) => ({ title: a.title || "Farm notification", body: a.message || a.body || "New field notification.", time: a.created_at ? new Date(a.created_at).toLocaleString() : "Recently", icon: <Bell /> })) : [{ title: "No live alerts yet", body: "Your notification feed will appear here when the backend reports a field event.", time: "Waiting for telemetry", icon: <Bell /> }]; return <ViewFrame eyebrow="ATTENTION" title="Field alerts" subtitle="Important changes are kept here so nothing gets missed."><div className="alerts-list">{items.map((a, i) => <button className={`alert-row ${i === 0 && alerts.length ? "unread" : ""}`} key={`${a.title}-${i}`} onClick={() => onToast("Alert marked as reviewed.")}><div className="alert-icon">{a.icon}</div><div><strong>{a.title}</strong><p>{a.body}</p><span>{a.time}</span></div><ChevronRight size={18} /></button>)}</div></ViewFrame>; }
function ViewFrame({ eyebrow, title, subtitle, children }: { eyebrow: string; title: string; subtitle: string; children: React.ReactNode }) { return <div className="view-frame"><div className="view-heading"><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p>{subtitle}</p></div>{children}</div>; }
