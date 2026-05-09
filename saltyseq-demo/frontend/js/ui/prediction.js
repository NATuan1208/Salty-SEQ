/* ── Risk Needle Gauge + PredictionForm + ResultCard ── */
(function () {
  const { useState, useEffect, useRef } = React;

  /* ═══════════════════════════════════════════════════
     RISK NEEDLE GAUGE — speedometer style, semi-circle
     Left (0%) → Top (50%) → Right (100%)
     3 colour zones: SAFE 0–35% | WARNING 35–60% | DANGER 60–100%
     Needle animates to probability position.
     Design rationale: model outputs are near-binary (0% or ~100%),
     so a filled arc is meaningless. A needle always has a visible
     position regardless of probability magnitude.
  ═══════════════════════════════════════════════════ */
  function CircularGauge({ probability, label, confidence }) {
    const [disp, setDisp] = useState(0);

    useEffect(() => {
      setDisp(0);
      const target = probability * 100;
      let frame;
      const t0 = performance.now(), dur = 1600;
      const tick = now => {
        const p = Math.min((now - t0) / dur, 1);
        setDisp((1 - Math.pow(1 - p, 3)) * target);
        if (p < 1) frame = requestAnimationFrame(tick);
      };
      frame = requestAnimationFrame(tick);
      return () => cancelAnimationFrame(frame);
    }, [probability]);

    /* ── Geometry ─────────────────────────────────────
       Semi-circle: center pinned to bottom of SVG.
       angleRad = π + (p/100)*π
         p=0%  → π   = LEFT
         p=50% → 3π/2 = TOP (up in SVG because sin(3π/2)=-1)
         p=100%→ 2π  = RIGHT
       Arc SVG command uses sweep=1 (clockwise on screen) to
       traverse LEFT → TOP → RIGHT.
    ─────────────────────────────────────────────────── */
    const W = 260, H = 148;
    const CX = W / 2, CY = H;   // 130, 148
    const R  = 108, SW = 22, RN = 92;

    const toRad = p => Math.PI + (p / 100) * Math.PI;
    const pt = (p, r) => [
      CX + r * Math.cos(toRad(p)),
      CY + r * Math.sin(toRad(p)),
    ];
    /* SVG arc from p1% to p2%, sweep=1 = clockwise = LEFT→TOP→RIGHT */
    const arc = (p1, p2, r = R) => {
      const [x1, y1] = pt(p1, r);
      const [x2, y2] = pt(p2, r);
      return `M ${x1.toFixed(2)} ${y1.toFixed(2)} A ${r} ${r} 0 ${(p2 - p1) > 50 ? 1 : 0} 1 ${x2.toFixed(2)} ${y2.toFixed(2)}`;
    };

    /* Needle endpoint */
    const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
    const [nx, ny] = pt(clamp(disp, 0, 100), RN);

    /* Colors */
    const col    = probability >= 0.6 ? '#C82020' : probability >= 0.35 ? '#C48020' : '#0FA860';
    const cssVar = probability >= 0.6 ? 'var(--danger-5)' : probability >= 0.35 ? 'var(--warn-5)' : 'var(--safe-5)';
    const viLabel = { DANGER:'NGUY HIỂM', WARNING:'CẢNH BÁO', SAFE:'AN TOÀN' };
    const icon    = { DANGER:'⚠', WARNING:'⚠', SAFE:'✓' };

    /* Displayed text: 1 decimal always */
    const dispText = disp.toFixed(1);

    return (
      <div className="gauge-wrap">
        <svg width={W} height={H + 22} viewBox={`0 0 ${W} ${H + 22}`} style={{ overflow:'visible' }}>
          <defs>
            <filter id="ng-glow" x="-30%" y="-30%" width="160%" height="160%">
              <feGaussianBlur stdDeviation="2.5" result="blur"/>
              <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
            </filter>
          </defs>

          {/* ── Background track (full semi-circle) ── */}
          <path d={arc(0, 100)} fill="none" stroke="var(--surface-3)" strokeWidth={SW} strokeLinecap="round"/>

          {/* ── Coloured zone segments ── */}
          <path d={arc(0.5, 34.5)} fill="none" stroke="#0FA860" strokeWidth={SW - 6} strokeOpacity=".35" strokeLinecap="butt"/>
          <path d={arc(35.5, 59.5)} fill="none" stroke="#C48020" strokeWidth={SW - 6} strokeOpacity=".35" strokeLinecap="butt"/>
          <path d={arc(60.5, 99.5)} fill="none" stroke="#C82020" strokeWidth={SW - 6} strokeOpacity=".35" strokeLinecap="butt"/>

          {/* ── Threshold marker at 50% (dashed tick) ── */}
          {(([ix, iy], [ox, oy]) =>
            <line x1={ix} y1={iy} x2={ox} y2={oy}
              stroke="var(--ink-3)" strokeWidth="1.8" strokeDasharray="3 2" strokeLinecap="round"/>
          )(pt(50, R - SW / 2 + 1), pt(50, R + SW / 2 + 10))}

          {/* ── Tick marks at 0, 25, 50, 75, 100 ── */}
          {[0, 25, 50, 75, 100].map(pct => {
            const [ix, iy] = pt(pct, R - SW / 2 + 2);
            const [ox, oy] = pt(pct, R + SW / 2 + (pct % 50 === 0 ? 8 : 4));
            return <line key={pct} x1={ix} y1={iy} x2={ox} y2={oy}
              stroke={pct % 50 === 0 ? 'var(--ink-2)' : 'var(--border-md)'}
              strokeWidth={pct % 50 === 0 ? 2 : 1.2} strokeLinecap="round"/>;
          })}

          {/* ── Tick labels: 0 and 100 hardcoded to avoid overflow, 50 computed ── */}
          <text x="10"     y={CY}    textAnchor="middle" dominantBaseline="middle" fontSize="9" fontFamily="JetBrains Mono, monospace" fill="var(--ink-4)">0</text>
          <text x={W - 10} y={CY}    textAnchor="middle" dominantBaseline="middle" fontSize="9" fontFamily="JetBrains Mono, monospace" fill="var(--ink-4)">100</text>
          {(([lx, ly]) =>
            <text x={lx} y={ly} textAnchor="middle" dominantBaseline="middle" fontSize="9" fontFamily="JetBrains Mono, monospace" fill="var(--ink-4)">50</text>
          )(pt(50, R + SW / 2 + 19))}

          {/* ── Zone labels at very bottom ── */}
          <text x={CX - 80} y={CY + 18} textAnchor="middle" fontSize="8" fontFamily="Nunito, sans-serif" fontWeight="800" fill="#0FA860" fillOpacity=".75">AN TOÀN</text>
          <text x={CX}      y={CY + 18} textAnchor="middle" fontSize="8" fontFamily="Nunito, sans-serif" fontWeight="800" fill="#C48020" fillOpacity=".75">NGƯỠNG 50%</text>
          <text x={CX + 80} y={CY + 18} textAnchor="middle" fontSize="8" fontFamily="Nunito, sans-serif" fontWeight="800" fill="#C82020" fillOpacity=".75">NGUY HIỂM</text>

          {/* ── Needle glow halo ── */}
          <line x1={CX} y1={CY} x2={nx} y2={ny} stroke={col} strokeWidth="10" strokeLinecap="round" strokeOpacity=".18"/>
          {/* ── Needle ── */}
          <line x1={CX} y1={CY} x2={nx} y2={ny} stroke={col} strokeWidth="3.2" strokeLinecap="round" filter="url(#ng-glow)"/>

          {/* ── Hub (layered circles for depth) ── */}
          <circle cx={CX} cy={CY} r="12" fill="var(--surface)" stroke={col} strokeWidth="2.5"/>
          <circle cx={CX} cy={CY} r="6"  fill={col}/>
          <circle cx={CX} cy={CY} r="2.5" fill="var(--surface)"/>

          {/* ── Probability % — large number inside arc ── */}
          <text x={CX} y={CY - 42}
            textAnchor="middle" dominantBaseline="middle"
            fontSize="44" fontFamily="JetBrains Mono, monospace" fontWeight="700"
            fill={col}>
            {dispText}
          </text>
          <text x={CX} y={CY - 14}
            textAnchor="middle"
            fontSize="11.5" fontFamily="Nunito, sans-serif"
            fill="var(--ink-4)" letterSpacing=".04em">
            % xác suất stress
          </text>
        </svg>

        {/* Label + confidence */}
        <div className="gauge-label-row">
          <span className={`gauge-label ${label}`}>{icon[label]} {viLabel[label]}</span>
          <span className={`conf-pill ${confidence}`}>{confidence}</span>
        </div>

        {/* Stats row */}
        <div className="gauge-meta">
          <div className="gauge-stat">
            <span className="gauge-stat-label">Threshold</span>
            <span className="gauge-stat-val">50%</span>
          </div>
          <div className="gauge-divider"/>
          <div className="gauge-stat">
            <span className="gauge-stat-label">Score</span>
            <span className="gauge-stat-val" style={{ color: cssVar }}>
              {(probability * 100).toFixed(2)}%
            </span>
          </div>
          <div className="gauge-divider"/>
          <div className="gauge-stat">
            <span className="gauge-stat-label">Conf.</span>
            <span className="gauge-stat-val">{confidence}</span>
          </div>
        </div>
      </div>
    );
  }

  /* ── Accordion feature group ── */
  function AccGroup({ group, features, onChange, open, onToggle }) {
    return (
      <div className="acc-wrap">
        <button className={`acc-trigger${open ? ' open' : ''}`} onClick={onToggle}>
          <i className={`ti ${group.icon} ti-sm`}/>
          {group.label}
          <i className="ti ti-chevron-down" style={{ marginLeft:'auto', fontSize:'12px' }}/>
        </button>
        {open && (
          <div className="acc-body">
            {group.fields.map(f => (
              <div key={f.key} className="fi-wrap">
                <label className="fi-label">{f.label}</label>
                <input
                  type="number"
                  className="fi-inp"
                  step={f.step}
                  value={features[f.key] ?? ''}
                  onChange={e => onChange(f.key, parseFloat(e.target.value) || 0)}
                  placeholder="—"
                />
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  /* ── Result card (wraps gauge + top features) ── */
  function ResultCard({ result }) {
    if (!result) return null;
    const cls = result.label === 'DANGER' ? 'result-danger'
              : result.label === 'WARNING' ? 'result-warning'
              : 'result-safe';
    return (
      <div className={`card fade-in ${cls}`} style={{ marginBottom:0 }}>
        <CircularGauge
          probability={result.probability}
          label={result.label}
          confidence={result.confidence}
        />

        {result.feature_top10?.length > 0 && (
          <div style={{ marginTop:'14px', paddingTop:'12px', borderTop:'1px solid var(--border)' }}>
            <div style={{
              fontSize:'10.5px', fontWeight:700, color:'var(--ink-4)',
              textTransform:'uppercase', letterSpacing:'.07em',
              marginBottom:'9px', display:'flex', alignItems:'center', gap:'5px',
            }}>
              <i className="ti ti-flame ti-sm" style={{ color:'var(--gold-6)' }}/>
              Top 3 Features ảnh hưởng
            </div>
            {result.feature_top10.slice(0, 3).map((f, i) => (
              <div key={i} className="top-feat">
                <span className="top-feat-rank">#{i + 1}</span>
                <span className="top-feat-name">{f.feature}</span>
                {f.value != null && (
                  <span className="top-feat-val">
                    {typeof f.value === 'number' ? f.value.toFixed(3) : f.value}
                  </span>
                )}
                <span className="top-feat-gain">gain {f.importance}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  /* ── Center Panel ── */
  /* selectedStation: controlled from App when user clicks map marker or station list */
  function PredictionPanel({ stations, selectedStation, onResult, onShowToast }) {
    const DEMO_DATE = '2020-03-15'; // good dry-season demo date inside CSV range
    const [station, setStation]   = useState('');
    const [date,    setDate]      = useState(DEMO_DATE);
    const [features, setFeatures] = useState({});
    const [result,  setResult]    = useState(null);
    const [loading, setLoading]   = useState(false);
    const [loadingD, setLoadingD] = useState(false);
    const [acc, setAcc] = useState({ veg:true, sal:true, climate:false, soil:false });
    const resultRef = useRef(null);

    /* Propagate result up to App */
    useEffect(() => { onResult && onResult(result, station); }, [result]);

    /* When stations first load, pick the first station */
    useEffect(() => {
      if (stations.length && !station) setStation(stations[0].station_id);
    }, [stations]);

    /* Sync station when user clicks map marker or station list (selectedStation prop) */
    useEffect(() => {
      if (!selectedStation || selectedStation === station) return;
      setStation(selectedStation);
      setResult(null);
    }, [selectedStation]);

    /* Auto-load CSV data whenever station or date changes */
    useEffect(() => {
      if (!station || !date) return;
      loadDataSilent();
    }, [station, date]);

    const setFeat = (k, v) => setFeatures(prev => ({ ...prev, [k]: v }));
    const toggleAcc = k => setAcc(prev => ({ ...prev, [k]: !prev[k] }));

    /* Load data and return the features (for use in handlePredict) */
    async function fetchFeatures(sid, dt) {
      try {
        const d = await MS.api.get(`/data/${sid}/${dt}`);
        setFeatures(d);
        return d;
      } catch (e) {
        onShowToast(`Lỗi tải dữ liệu: ${e.message}`, 'error');
        return null;
      }
    }

    /* Auto-load triggered by station/date change — shows loading indicator */
    async function loadDataSilent() {
      if (!station || !date) return;
      setLoadingD(true);
      await fetchFeatures(station, date);
      setLoadingD(false);
    }

    /* Manual load button — with success/error toast */
    async function loadData() {
      if (!station || !date) return;
      setLoadingD(true);
      const d = await fetchFeatures(station, date);
      setLoadingD(false);
      if (d) onShowToast('Dữ liệu đã được tải từ CSV', 'success');
    }

    async function handlePredict() {
      if (!station || !date) { onShowToast('Chọn trạm và ngày trước', 'info'); return; }
      setLoading(true);
      try {
        /* If features not loaded yet, fetch now (handles race condition) */
        let featsToSend = features;
        if (Object.keys(featsToSend).length === 0) {
          setLoadingD(true);
          const d = await fetchFeatures(station, date);
          setLoadingD(false);
          featsToSend = d || {};
        }
        const d = await MS.api.post('/predict', { station_id: station, date, features: featsToSend });
        setResult(d);
        setTimeout(() => resultRef.current?.scrollIntoView({ behavior:'smooth', block:'nearest' }), 200);
      } catch (e) { onShowToast(`Lỗi dự báo: ${e.message}`, 'error'); }
      finally { setLoading(false); }
    }

    return (
      <div className="panel panel-center">
        {/* Section header */}
        <div className="sec-title">
          <i className="ti ti-chart-histogram ti-md"/>
          Phân tích &amp; Dự báo
          {result && (
            <span className="sec-title-badge" style={{
              color: result.label === 'DANGER' ? 'var(--danger-5)' : result.label === 'WARNING' ? 'var(--warn-5)' : 'var(--safe-5)',
              borderColor: result.label === 'DANGER' ? 'var(--danger-bd)' : result.label === 'WARNING' ? 'var(--warn-bd)' : 'var(--safe-bd)',
              background: result.label === 'DANGER' ? 'var(--danger-lt)' : result.label === 'WARNING' ? 'var(--warn-lt)' : 'var(--safe-lt)',
            }}>
              {result.label}
            </span>
          )}
        </div>

        {/* Station + date */}
        <div className="card">
          <div className="card-title">
            <i className="ti ti-map-pin ti-sm" style={{ color:'var(--gold-6)' }}/>
            Điểm quan trắc &amp; Thời gian
          </div>
          <div className="form-row">
            <div className="field">
              <label className="field-label">
                <i className="ti ti-building-broadcast-tower ti-xs"/>
                Trạm
              </label>
              <select className="fctl" value={station}
                onChange={e => { setStation(e.target.value); setResult(null); }}>
                <option value="">— Chọn trạm —</option>
                {stations.map(s => (
                  <option key={s.station_id} value={s.station_id}>{s.name}</option>
                ))}
              </select>
            </div>
            <div className="field">
              <label className="field-label">
                <i className="ti ti-calendar ti-xs"/>
                Ngày
              </label>
              <input type="date" className="fctl" value={date}
                min="2015-01-01"
                max="2025-12-31"
                onChange={e => { setDate(e.target.value); setResult(null); }}
              />
            </div>
          </div>
          <button className="btn-load" onClick={loadData} disabled={loadingD || !station || !date}>
            {loadingD
              ? <><span className="spinner dark" style={{ width:'13px', height:'13px', borderWidth:'1.5px' }}/> Đang tải…</>
              : <><i className="ti ti-database-import ti-sm"/> Tải dữ liệu từ merged_final.csv</>
            }
          </button>
        </div>

        {/* Feature accordion */}
        <div className="card" style={{ padding:'12px 14px' }}>
          <div className="card-title">
            <i className="ti ti-sliders ti-sm" style={{ color:'var(--teal-5)' }}/>
            Thông số đầu vào — 46 features
          </div>
          {Object.entries(MS.FEATURE_GROUPS).map(([k, g]) => (
            <AccGroup key={k} group={g} features={features}
              onChange={setFeat} open={acc[k]} onToggle={() => toggleAcc(k)}/>
          ))}
        </div>

        {/* Analyze CTA */}
        <button className="btn-analyze" onClick={handlePredict}
          disabled={loading || loadingD || !station || !date}>
          {loading
            ? <><span className="spinner"/> Đang phân tích…</>
            : loadingD
            ? <><span className="spinner"/> Đang tải dữ liệu…</>
            : <><i className="ti ti-bolt" style={{ fontSize:'18px' }}/> PHÂN TÍCH NGAY</>
          }
        </button>

        {/* Result */}
        <div ref={resultRef}>
          <ResultCard result={result}/>
        </div>
      </div>
    );
  }

  MS.PredictionPanel = PredictionPanel;
  MS.CircularGauge  = CircularGauge;
}());
