import { useState, useRef, useCallback, useEffect } from 'react'
import { Truck, ArrowRight, ArrowUpRight, Layers, Wind, CloudRain, Snowflake, Route as RouteIcon, ShieldCheck, Clock, ChevronRight, LocateFixed } from 'lucide-react'
import PlaceSearch from './PlaceSearch'
import MapView from './MapView'
import { api } from './api'
import type { Assessment, Checkpoint, Corridor, Place } from './types'
import { colors, labels, routeColors, time, duration } from './types'
function localInput() { const d = new Date(Date.now() + 3600000); d.setMinutes(d.getMinutes() - d.getTimezoneOffset()); return d.toISOString().slice(0, 16) }
export default function App() {
    const [origin, setOrigin] = useState<Place | null>(null), [destination, setDestination] = useState<Place | null>(null)
    const [departure, setDeparture] = useState(localInput), [load, setLoad] = useState(30000), [interval, setInterval] = useState(25)
    const [data, setData] = useState<Assessment | null>(null), [selected, setSelected] = useState(''), [checkpoint, setCheckpoint] = useState<Checkpoint | null>(null)
    const [corridor, setCorridor] = useState<Corridor | null>(null), [hour, setHour] = useState(0), [showHeat, setShowHeat] = useState(true)
    const [busy, setBusy] = useState(false), [heatBusy, setHeatBusy] = useState(false), [error, setError] = useState(''), [heatError, setHeatError] = useState('')
    const [tripLabel, setTripLabel] = useState(''), [assessedLoad, setAssessedLoad] = useState(load)
    const requestId = useRef(0)
    const selectionTouched = useRef(false)
    useEffect(() => () => { requestId.current += 1 }, [])
    const chooseRoute = useCallback((id: string) => {
        selectionTouched.current = true
        setSelected(id)
        setCheckpoint(null)
    }, [])
    async function plan(e: React.FormEvent) {
        e.preventDefault()
        if (!origin || !destination) return
        const id = ++requestId.current
        const payload = { origin: origin.coordinate, destination: destination.coordinate, departure: new Date(departure).toISOString(), load_lb: load, interval_miles: interval }
        selectionTouched.current = false
        setBusy(true); setHeatBusy(false); setError(''); setHeatError('')
        setData(null); setCorridor(null); setCheckpoint(null); setHour(0)
        setTripLabel(origin.label.split(',')[0] + ' → ' + destination.label.split(',')[0])
        setAssessedLoad(load)
        try {
            const preview = await api<Assessment>('routes/', payload)
            if (id !== requestId.current) return
            setData(preview); setSelected(preview.routes[0].id); setHeatBusy(true)
            // Map and ETAs are usable immediately; corridor and checkpoint
            // weather can finish independently without blocking each other.
            void api<Corridor>('corridor/', { geometries: preview.routes.map(r => r.geometry), load_lb: payload.load_lb })
                .then(result => { if (id === requestId.current) setCorridor(result) })
                .catch(e => { if (id === requestId.current) setHeatError((e as Error).message) })
                .finally(() => { if (id === requestId.current) setHeatBusy(false) })
            const result = await api<Assessment>('assess/', payload)
            if (id !== requestId.current) return
            setData(result)
            setSelected(previous => selectionTouched.current && result.routes.some(r => r.id === previous) ? previous : result.recommended_id || result.routes[0].id)
        } catch (e) {
            if (id === requestId.current) {
                setError((e as Error).message)
                setData(previous => previous ? { ...previous, assessment_status: 'failed' } : null)
            }
        } finally {
            if (id === requestId.current) setBusy(false)
        }
    }
    const forecast = corridor ? new Date(new Date(corridor.anchor).getTime() + hour * 3600000).toISOString() : null
    const worst = corridor?.samples.reduce((max, s) => Math.max(max, s.hours[hour]?.risk.score ?? -1), -1) ?? -1
    return <div className="app">
        <header className="topbar"><a href="/" className="brand"><span className="brand-icon"><Truck size={22} /></span>weather<span>haul</span></a><span className="nav-label">ROUTE INTELLIGENCE</span><div className="top-meta"><span className="status-dot" />Live weather routing<span className="version">ASSESSMENT / V1.0</span></div></header>
        <main className="workspace">
            <aside className="sidebar"><div className="sidebar-heading"><span className="eyebrow">PLAN WITH CONFIDENCE</span><h1>A clearer road ahead.</h1><p>Compare routes with the weather<br />your truck will actually meet.</p></div>
                <form onSubmit={e => void plan(e)}><div className="section-label"><span>01</span>Trip details</div>
                    <PlaceSearch label="Origin" value={origin} onChange={setOrigin} /><div className="route-connector">⋮</div><PlaceSearch label="Destination" value={destination} onChange={setDestination} />
                    <label className="field">Departure <span className="subtle">Your local time</span><input type="datetime-local" value={departure} onChange={e => setDeparture(e.target.value)} required /></label>
                    <div className="field-row"><label className="field">Load weight <div className="unit-input"><input type="number" value={load} min="0" max="200000" required onChange={e => setLoad(Number(e.target.value))} /><span>lb</span></div></label><label className="field">Checkpoints<select aria-label="Checkpoints" value={interval} onChange={e => setInterval(Number(e.target.value))}>{[10, 25, 50].map(n => <option key={n} value={n}>{n} miles</option>)}</select></label></div>
                    <button className="primary" type="submit" disabled={busy || !origin || !destination}>{busy ? <><span className="spinner" />{data ? "Checking weather..." : "Finding routes..."}</> : <>Find safest route<ArrowRight size={17} /></>}</button>
                    {!origin && !destination && <p className="form-hint">Search each location and select a result to begin.</p>}
                    {error && <div className="error" role="alert">{error}</div>}
                </form>
                <section className="comparison"><div className="section-label"><span>02</span>Route comparison{data && <small>{data.routes.length} AVAILABLE</small>}</div>
                    {!data ? <div className="empty-comparison"><RouteIcon size={28} /><p>Your options, side by side.</p><span>Distance, arrival-time risk and travel time<br />will appear after you plan a trip.</span></div> : <>
                        {data.warnings.map(w => <p className="warning" key={w}>{w}</p>)}
                        {!busy && data.assessment_status !== "failed" && !data.recommended_id && <p className="error">No route can be recommended. Check restrictions and weather coverage before departure.</p>}
                        {[0, 1, 2].map(i => {
                            const r = data.routes[i]
                            if (!r) return <div className="unavailable" key={i}>Route {String.fromCharCode(65 + i)} <span>No distinct reasonable route found</span></div>
                            const pending = data.assessment_status === 'pending'
                            const failed = data.assessment_status === 'failed'
                            const arrival = r.checkpoints.at(-1)?.eta
                            return <button type="button" key={r.id} aria-pressed={selected === r.id} className={'route-card ' + (selected === r.id ? 'selected' : '')} style={{ '--route-color': routeColors[i] } as React.CSSProperties} onClick={() => chooseRoute(r.id)}>
                                <div className="route-card-top"><strong><span className="route-line" />Route {String.fromCharCode(65 + i)}</strong>{pending ? <span className="subtle">Checking weather</span> : r.id === data.recommended_id ? <span className="recommended"><ShieldCheck size={12} />Recommended</span> : <span className="subtle">{r.eligible && !failed ? 'Alternative' : 'Not eligible'}</span>}</div>
                                <div className="route-card-stats"><b>{duration(r.duration_seconds)}</b><span>{r.distance_miles.toFixed(0)} mi</span><ChevronRight size={16} /></div>
                                {arrival && <div className="route-arrival"><Clock size={13} /><div><span>Estimated arrival</span><time dateTime={arrival}>{time(arrival)}</time></div></div>}
                                {r.route_kind === 'via_waypoint' && <span className="route-via">Via alternate road corridor</span>}
                                {pending || failed ? <div className="route-weather-status" role="status">{pending ? <><span className="spinner" />Assessing checkpoint weather...</> : 'Weather assessment unavailable'}</div> : <><div className="risk-stats"><span><i style={{ background: colors[3] }} />{r.risk_miles.Severe.toFixed(1)} severe mi</span><span><i style={{ background: colors[2] }} />{r.risk_miles.High.toFixed(1)} high mi</span></div><div className="route-foot">Avg risk {r.average_risk?.toFixed(2) ?? 'unavailable'}{r.risk_miles['No Travel'] > 0 && ' / ' + r.risk_miles['No Travel'].toFixed(1) + ' no-travel mi'}{r.unknown_miles > 0 && ' / ' + r.unknown_miles.toFixed(1) + ' unknown mi'}</div></>}
                            </button>
                        })}
                        <p className="ranking-note">Ranked by severe miles, high miles, average risk, then travel time. Restricted or incomplete routes are excluded.</p>
                    </>}
                </section>
                <footer className="sidebar-footer"><ShieldCheck size={15} /><span>Weather guidance. Always follow road closures<br />and official travel advisories.</span></footer>
            </aside>
            <section className="map-section" aria-label="Route map and forecasts">
                <MapView data={data} selected={selected} onSelect={chooseRoute} onCheckpoint={setCheckpoint} corridor={corridor} hour={hour} showHeat={showHeat} />
                <div className="map-top"><div className="map-title"><span className="eyebrow">JOURNEY OVERVIEW</span><h2>{tripLabel || 'Every mile. In perspective.'}</h2><p>{data ? 'Arrival-time checkpoint assessment · ' + assessedLoad.toLocaleString() + ' lb load' : 'Plan a trip to reveal routes and weather ahead.'}</p></div><button type="button" className={'layer-button ' + (showHeat ? 'active' : '')} disabled={!corridor} onClick={() => setShowHeat(!showHeat)} aria-pressed={showHeat}><Layers size={16} />Weather layer</button></div>
                {!data && !busy && <div className="map-empty"><span className="map-empty-icon"><LocateFixed size={26} /></span><h3>The journey starts here.</h3><p>Set your origin and destination to compare<br />weather along the road ahead.</p><span>REAL ROUTES · ARRIVAL-TIME FORECASTS</span></div>}
                {busy && !data && <div className="map-loading" role="status"><span className="spinner" />Finding distinct road routes...</div>}
                {checkpoint && <div className="checkpoint-panel"><button className="close" type="button" onClick={() => setCheckpoint(null)} aria-label="Close checkpoint">×</button><span className="eyebrow">ARRIVAL-TIME CHECKPOINT</span><h3>Mile {checkpoint.mile.toFixed(1)} <span style={{ color: checkpoint.risk ? colors[checkpoint.risk.score] : '#777' }}>{checkpoint.risk?.label || 'Unknown'}</span></h3><p>{time(checkpoint.eta)}</p><div className="weather-values"><span><Wind size={16} />{checkpoint.weather?.wind_mph.toFixed(1) ?? '—'} mph</span><span><CloudRain size={16} />{checkpoint.weather?.rain_in_hr.toFixed(3) ?? '—'} in/hr</span><span><Snowflake size={16} />{checkpoint.weather?.snow_in_hr.toFixed(3) ?? '—'} in/hr</span></div><p>{checkpoint.risk?.reasons.join(' · ') || 'Weather unavailable; route cannot be recommended.'}</p></div>}
                <div className="map-bottom"><div className="legend"><span>WEATHER RISK</span>{labels.map((label, i) => <span key={label}><i style={{ background: colors[i] }} />{label}</span>)}<span><i style={{ background: '#87939b' }} />Unknown</span></div>
                    <div className="timeline"><div className="timeline-heading"><div><span className="eyebrow">CORRIDOR FORECAST</span><h3>{forecast ? time(forecast) : 'Explore the next 48 hours'}</h3></div><span className="forecast-badge">{heatBusy ? 'Loading weather…' : corridor ? '+' + hour + 'h' : 'AWAITING TRIP'}</span></div>
                        <input aria-label="Forecast hour" type="range" min="0" max="48" step="1" value={hour} disabled={!corridor} onChange={e => setHour(Number(e.target.value))} /><div className="timeline-ticks"><span>Now</span><span>+12h</span><span>+24h</span><span>+36h</span><span>+48h</span></div><p>{heatError ? <span role="alert" className="field-error">{heatError}</span> : corridor ? <>Corridor snapshot · peak sampled risk: <strong style={{ color: worst >= 0 ? colors[worst] : '#777' }}>{worst >= 0 ? labels[worst] : 'Unknown'}</strong>. Checkpoint assessments use arrival times.</> : 'A live weather layer across the trip corridor. Checkpoint risks use your estimated arrival times.'}</p>
                    </div>
                </div>
            </section>
        </main><footer className="bottom-bar"><span>Built for better-informed journeys.</span><span>Routing: OSRM · Weather: {data?.weather_provider ? <a href={data.weather_provider.url}>{data.weather_provider.name}</a> : "forecasts"} · Geocoding: OpenStreetMap <ArrowUpRight size={12} /></span></footer>
    </div>
}
