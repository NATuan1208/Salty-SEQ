/* ── Risk Needle Gauge + PredictionForm + ResultCard ── */
(function () {
  const { useState, useEffect, useRef } = React;

  /* ═══════════════════════════════════════════════════
     RISK NEEDLE GAUGE — speedometer style, semi-circle
     Left (0%) → Top (50%) → Right (100%)
     3 colour zones: SAFE <5% | WARNING 5–15% | DANGER >15%
     Needle animates to probability position.
  ═══════════════════════════════════════════════════ */
  function CircularGauge({ probability, label, confidence, confidenceDetail }) {
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

    const W = 260, H = 148;
    const CX = W / 2, CY = H;
    const R  = 108, SW = 22, RN = 92;

    const toRad = p => Math.PI + (p / 100) * Math.PI;
    const pt = (p, r) => [
      CX + r * Math.cos(toRad(p)),
      CY + r * Math.sin(toRad(p)),
    ];
    const arc = (p1, p2, r = R) => {
      const [x1, y1] = pt(p1, r);
      const [x2, y2] = pt(p2, r);
      return `M ${x1.toFixed(2)} ${y1.toFixed(2)} A ${r} ${r} 0 0 1 ${x2.toFixed(2)} ${y2.toFixed(2)}`;
    };

    const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
    const [nx, ny] = pt(clamp(disp, 0, 100), RN);

    const col    = probability >= 0.15 ? '#C82020' : probability >= 0.05 ? '#C48020' : '#0FA860';
    const cssVar = probability >= 0.15 ? 'var(--danger-5)' : probability >= 0.05 ? 'var(--warn-5)' : 'var(--safe-5)';
    const viLabel = { DANGER:'NGUY HIỂM', WARNING:'CẢNH BÁO', SAFE:'AN TOÀN' };
    const icon    = { DANGER:'⚠', WARNING:'⚠', SAFE:'✓' };
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

          <path d={arc(0, 100)} fill="none" stroke="var(--surface-3)" strokeWidth={SW} strokeLinecap="round"/>

          <path d={arc(0.5, 4.8)} fill="none" stroke="#0FA860" strokeWidth={SW - 6} strokeOpacity=".42" strokeLinecap="butt"/>
          <path d={arc(5.2, 14.8)} fill="none" stroke="#C48020" strokeWidth={SW - 6} strokeOpacity=".50" strokeLinecap="butt"/>
          <path d={arc(15.2, 99.5)} fill="none" stroke="#C82020" strokeWidth={SW - 6} strokeOpacity=".35" strokeLinecap="butt"/>

          {(([ix, iy], [ox, oy]) =>
            <line x1={ix} y1={iy} x2={ox} y2={oy}
              stroke="var(--ink-3)" strokeWidth="1.8" strokeDasharray="3 2" strokeLinecap="round"/>
          )(pt(5, R - SW / 2 + 1), pt(5, R + SW / 2 + 10))}

          {[0, 5, 15, 50, 100].map(pct => {
            const [ix, iy] = pt(pct, R - SW / 2 + 2);
            const [ox, oy] = pt(pct, R + SW / 2 + (pct === 0 || pct === 100 ? 8 : 5));
            return <line key={pct} x1={ix} y1={iy} x2={ox} y2={oy}
              stroke={pct === 0 || pct === 100 ? 'var(--ink-2)' : 'var(--border-md)'}
              strokeWidth={pct === 0 || pct === 100 ? 2 : 1.4} strokeLinecap="round"/>;
          })}

          <text x="10"     y={CY}    textAnchor="middle" dominantBaseline="middle" fontSize="9" fontFamily="JetBrains Mono, monospace" fill="var(--ink-4)">0</text>
          <text x={W - 10} y={CY}    textAnchor="middle" dominantBaseline="middle" fontSize="9" fontFamily="JetBrains Mono, monospace" fill="var(--ink-4)">100</text>
          {(([lx, ly]) =>
            <text x={lx} y={ly} textAnchor="middle" dominantBaseline="middle" fontSize="9" fontFamily="JetBrains Mono, monospace" fill="var(--ink-4)">5</text>
          )(pt(5, R + SW / 2 + 19))}
          {(([lx, ly]) =>
            <text x={lx} y={ly} textAnchor="middle" dominantBaseline="middle" fontSize="9" fontFamily="JetBrains Mono, monospace" fill="var(--ink-4)">15</text>
          )(pt(15, R + SW / 2 + 19))}

          <rect x="0" y={CY + 7} width={W} height="19" fill="var(--surface)" opacity=".96"/>
          <text x={CX - 78} y={CY + 18} textAnchor="middle" fontSize="8" fontFamily="Nunito, sans-serif" fontWeight="800" fill="#0FA860" fillOpacity=".75">AN TOÀN &lt;5%</text>
          <text x={CX}      y={CY + 18} textAnchor="middle" fontSize="8" fontFamily="Nunito, sans-serif" fontWeight="800" fill="#C48020" fillOpacity=".75">CẢNH BÁO 5-15%</text>
          <text x={CX + 82} y={CY + 18} textAnchor="middle" fontSize="8" fontFamily="Nunito, sans-serif" fontWeight="800" fill="#C82020" fillOpacity=".75">NGUY HIỂM &gt;15%</text>

          <line x1={CX} y1={CY} x2={nx} y2={ny} stroke={col} strokeWidth="10" strokeLinecap="round" strokeOpacity=".18"/>
          <line x1={CX} y1={CY} x2={nx} y2={ny} stroke={col} strokeWidth="3.2" strokeLinecap="round" filter="url(#ng-glow)"/>

          <circle cx={CX} cy={CY} r="12" fill="var(--surface)" stroke={col} strokeWidth="2.5"/>
          <circle cx={CX} cy={CY} r="6"  fill={col}/>
          <circle cx={CX} cy={CY} r="2.5" fill="var(--surface)"/>

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

        <div className="gauge-label-row">
          <span className={`gauge-label ${label}`}>{icon[label]} {viLabel[label]}</span>
          <span
            className={`conf-pill ${confidence}`}
            title={confidenceDetail?.summary || 'Dựa trên độ chắc chắn của mô hình và độ đầy đủ dữ liệu.'}
          >
            {confidence}
          </span>
        </div>

        <div className="gauge-meta">
          <div className="gauge-stat">
            <span className="gauge-stat-label">Ngưỡng rủi ro</span>
            <span className="gauge-stat-val">5% / 15%</span>
          </div>
          <div className="gauge-divider"/>
          <div className="gauge-stat">
            <span className="gauge-stat-label">Điểm</span>
            <span className="gauge-stat-val" style={{ color: cssVar }}>
              {(probability * 100).toFixed(2)}%
            </span>
          </div>
          <div className="gauge-divider"/>
          <div className="gauge-stat">
            <span className="gauge-stat-label">Tin cậy</span>
            <span className="gauge-stat-val">{confidence}</span>
          </div>
        </div>

        <div className="confidence-note" title={confidenceDetail?.summary || ''}>
          <i className="ti ti-info-circle ti-sm"/>
          {confidenceDetail
            ? confidenceDetail.summary
            : 'Dựa trên độ chắc chắn của mô hình và độ đầy đủ dữ liệu.'}
        </div>
      </div>
    );
  }

  /* ═══════════════════════════════════════════════════
     CLICKABLE FEATURE LABEL
     Khi user click vào tên feature → navigate đến
     trang Đặc trưng và highlight feature đó.
  ═══════════════════════════════════════════════════ */
  function FeatureLabel({ fieldKey, label }) {
    /* Check if this feature key has an entry in the encyclopedia */
    const hasEntry = MS.FEATURE_MAP && MS.FEATURE_MAP[fieldKey];

    function handleClick(e) {
      e.preventDefault();
      if (MS.navigateToFeature) {
        MS.navigateToFeature(fieldKey);
      }
    }

    if (!hasEntry) {
      /* No entry: render plain label */
      return <span className="fi-label">{label}</span>;
    }

    return (
      <button
        className="fi-label fi-label-link"
        title={`Xem chi tiết: ${fieldKey} →`}
        onClick={handleClick}
        style={{
          background: 'none',
          border: 'none',
          padding: 0,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
          fontFamily: 'inherit',
          fontSize: 'inherit',
          color: 'inherit',
          textAlign: 'left',
          transition: 'color .15s',
        }}
        onMouseEnter={e => {
          e.currentTarget.style.color = 'var(--teal-5)';
          const icon = e.currentTarget.querySelector('.fi-link-icon');
          if (icon) icon.style.opacity = '1';
        }}
        onMouseLeave={e => {
          e.currentTarget.style.color = '';
          const icon = e.currentTarget.querySelector('.fi-link-icon');
          if (icon) icon.style.opacity = '0';
        }}
      >
        {label}
        <i
          className="ti ti-arrow-up-right fi-link-icon"
          style={{
            fontSize: '10px',
            opacity: 0,
            transition: 'opacity .15s',
            color: 'var(--teal-5)',
            flexShrink: 0,
          }}
        />
      </button>
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
                {/* ← Replaced plain <label> with clickable FeatureLabel */}
                <FeatureLabel fieldKey={f.key} label={f.label} />
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

  function csvCell(value) {
    const s = value == null ? '' : String(value);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  }

  function downloadText(filename, text, mime) {
    const blob = new Blob([text], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  function htmlEscape(value) {
    return String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function reportSections(result) {
    const exp = result.explanation || {};
    return {
      drivers: result.label === 'SAFE' ? [] : (exp.drivers || []),
      watchouts: result.label === 'SAFE'
        ? ((exp.watchouts?.length ? exp.watchouts : exp.drivers) || [])
        : (exp.watchouts || []),
      offsets: exp.offsets || [],
    };
  }

  function buildReportRows({ result, stationInfo, date, features }) {
    const sections = reportSections(result);
    const rows = [
      ['section', 'field', 'value'],
      ['summary', 'station', stationInfo?.name || ''],
      ['summary', 'station_id', stationInfo?.station_id || ''],
      ['summary', 'date', date],
      ['summary', 'label', result.label],
      ['summary', 'probability_percent', ((result.probability || 0) * 100).toFixed(2)],
      ['summary', 'confidence', result.confidence],
      ['summary', 'confidence_note', result.confidence_detail?.summary || ''],
      ['summary', 'explanation', result.explanation?.summary || ''],
    ];

    sections.drivers.forEach((d, i) => rows.push(['risk_driver', `${i + 1}.${d.feature}`, d.text]));
    sections.watchouts.forEach((d, i) => rows.push(['watchout', `${i + 1}.${d.feature}`, d.text]));
    sections.offsets.forEach((d, i) => rows.push(['mitigating_signal', `${i + 1}.${d.feature}`, d.text]));
    (result.recommendations || []).forEach((r, i) => rows.push(['recommendation', `${i + 1}`, r]));
    (result.feature_top10 || []).forEach((f, i) => rows.push(['feature_importance', `${i + 1}.${f.feature}`, `value=${f.value ?? ''}; gain=${f.importance}`]));

    Object.keys(features || {}).sort().forEach(k => {
      rows.push(['input_feature', k, features?.[k] ?? '']);
    });
    return rows;
  }

  function exportCsv({ result, stationInfo, date, features, onShowToast }) {
    const rows = buildReportRows({ result, stationInfo, date, features });
    const csv = '\ufeff' + rows.map(row => row.map(csvCell).join(',')).join('\n');
    const safeStation = (stationInfo?.station_id || 'station').replace(/[^a-z0-9_-]/gi, '_');
    downloadText(`saltyseq_${safeStation}_${date || 'report'}.csv`, csv, 'text/csv;charset=utf-8');
    onShowToast && onShowToast('Đã xuất báo cáo CSV', 'success');
  }

  function exportPdf({ result, stationInfo, date, features, onShowToast }) {
    const sections = reportSections(result);
    const featureRows = (result.feature_top10 || []).slice(0, 10).map((f, i) => `
      <tr><td>#${i + 1}</td><td>${htmlEscape(f.feature)}</td><td>${htmlEscape(f.value ?? '')}</td><td>${htmlEscape(f.importance)}</td></tr>
    `).join('');
    const list = (items) => items.length
      ? `<ul>${items.map(x => `<li>${htmlEscape(x.text || x)}</li>`).join('')}</ul>`
      : '<p class="muted">Không có.</p>';
    const win = window.open('', '_blank');
    if (!win) {
      onShowToast && onShowToast('Trình duyệt đang chặn popup xuất PDF', 'error');
      return;
    }
    win.document.write(`<!doctype html>
      <html lang="vi">
      <head>
        <meta charset="utf-8">
        <title>SaltySeq report</title>
        <style>
          body { font-family: Arial, sans-serif; color:#193018; margin:32px; line-height:1.5; }
          h1 { margin:0 0 4px; color:#0f7f54; font-size:26px; }
          h2 { margin:24px 0 8px; font-size:16px; color:#1a6f75; border-bottom:1px solid #d7e3d0; padding-bottom:6px; }
          .meta { color:#5f7f54; margin-bottom:18px; }
          .summary { border:1px solid #a9d8c3; background:#eefaf4; padding:14px; border-radius:8px; }
          .pill { display:inline-block; padding:3px 10px; border-radius:999px; border:1px solid #85d9b1; color:#0f9f65; font-weight:700; }
          .grid { display:grid; grid-template-columns:repeat(3, 1fr); gap:10px; margin:16px 0; }
          .box { border:1px solid #d7e3d0; border-radius:8px; padding:10px; }
          .box b { display:block; color:#7a9a62; font-size:12px; text-transform:uppercase; }
          table { width:100%; border-collapse:collapse; margin-top:8px; }
          th, td { text-align:left; border-bottom:1px solid #e1eadb; padding:7px 8px; font-size:13px; }
          th { color:#668a55; text-transform:uppercase; font-size:11px; }
          .muted { color:#78906e; }
          @media print { button { display:none; } body { margin:20mm; } }
        </style>
      </head>
      <body>
        <button onclick="window.print()">In / Lưu PDF</button>
        <h1>Mekong Sentinel - SaltySeq Report</h1>
        <div class="meta">${htmlEscape(stationInfo?.name || '')} · ${htmlEscape(date || '')} · ${htmlEscape(stationInfo?.distance_to_estuary_km ?? '')} km cửa biển</div>
        <div class="summary">
          <span class="pill">${htmlEscape(result.label)} · ${htmlEscape(result.confidence)}</span>
          <p>${htmlEscape(result.explanation?.summary || '')}</p>
          <p class="muted">${htmlEscape(result.confidence_detail?.summary || '')}</p>
        </div>
        <div class="grid">
          <div class="box"><b>Stress</b>${((result.probability || 0) * 100).toFixed(2)}%</div>
          <div class="box"><b>Salinity</b>${htmlEscape(features?.salinity_psu ?? '')} PSU</div>
          <div class="box"><b>NDVI</b>${htmlEscape(features?.ndvi ?? '')}</div>
        </div>
        <h2>Tín hiệu cảnh báo</h2>${list(sections.drivers)}
        <h2>Tín hiệu cần theo dõi</h2>${list(sections.watchouts)}
        <h2>Tín hiệu giảm rủi ro</h2>${list(sections.offsets)}
        <h2>Khuyến nghị</h2>${list(result.recommendations || [])}
        <h2>Top feature importance</h2>
        <table><thead><tr><th>Rank</th><th>Feature</th><th>Value</th><th>Gain</th></tr></thead><tbody>${featureRows}</tbody></table>
      </body></html>`);
    win.document.close();
    win.focus();
    onShowToast && onShowToast('Đã mở báo cáo PDF, chọn In / Lưu PDF', 'info');
  }

  /* ── Result card (wraps gauge + top features) ── */
  function ResultCard({ result, stationInfo, date, features, onShowToast }) {
    if (!result) return null;
    const cls = result.label === 'DANGER' ? 'result-danger'
              : result.label === 'WARNING' ? 'result-warning'
              : 'result-safe';
    const explanation = result.explanation;
    const drivers = result.label === 'SAFE' ? [] : (explanation?.drivers || []);
    const watchouts = result.label === 'SAFE'
      ? ((explanation?.watchouts?.length ? explanation.watchouts : explanation?.drivers) || [])
      : (explanation?.watchouts || []);
    return (
      <div className={`card fade-in ${cls}`} style={{ marginBottom:0 }}>
        <CircularGauge
          probability={result.probability}
          label={result.label}
          confidence={result.confidence}
          confidenceDetail={result.confidence_detail}
        />

        <div className="report-actions">
          <button className="btn-sm report" onClick={() => exportCsv({ result, stationInfo, date, features, onShowToast })}>
            <i className="ti ti-file-type-csv ti-sm"/> Xuất CSV
          </button>
          <button className="btn-sm report" onClick={() => exportPdf({ result, stationInfo, date, features, onShowToast })}>
            <i className="ti ti-file-type-pdf ti-sm"/> Xuất PDF
          </button>
        </div>

        {explanation && (
          <div className="why-card">
            <div className="why-head">
              <i className="ti ti-message-circle-question ti-sm"/>
              Vì sao mô hình dự báo như vậy?
            </div>
            <p className="why-summary">{explanation.summary}</p>
            {drivers.length > 0 && (
              <div className="why-list">
                {drivers.map((d, i) => (
                  <div key={`${d.feature}-${i}`} className={`why-item ${d.severity || 'medium'}`}>
                    <i className="ti ti-alert-triangle ti-sm"/>
                    <span>{d.text}</span>
                  </div>
                ))}
              </div>
            )}
            {watchouts.length > 0 && (
              <div className="why-watchouts">
                <div className="why-subhead">Tín hiệu cần theo dõi</div>
                {watchouts.map((d, i) => (
                  <div key={`${d.feature}-${i}`} className="why-item watch">
                    <i className="ti ti-eye-exclamation ti-sm"/>
                    <span>{d.text}</span>
                  </div>
                ))}
              </div>
            )}
            {explanation.offsets?.length > 0 && (
              <div className="why-offsets">
                {explanation.offsets.map((d, i) => (
                  <span key={`${d.feature}-${i}`}>
                    <i className="ti ti-shield-check ti-sm"/>
                    {d.text}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

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
                {/* Clickable feature name in result card too */}
                <button
                  className="top-feat-name"
                  style={{
                    background: 'none', border: 'none', padding: 0,
                    cursor: MS.FEATURE_MAP && MS.FEATURE_MAP[f.feature] ? 'pointer' : 'default',
                    fontFamily: 'inherit', fontSize: 'inherit', color: 'inherit',
                    textAlign: 'left', transition: 'color .15s',
                  }}
                  onClick={() => MS.FEATURE_MAP && MS.FEATURE_MAP[f.feature] && MS.navigateToFeature && MS.navigateToFeature(f.feature)}
                  onMouseEnter={e => { if (MS.FEATURE_MAP && MS.FEATURE_MAP[f.feature]) e.currentTarget.style.color = 'var(--teal-5)'; }}
                  onMouseLeave={e => { e.currentTarget.style.color = ''; }}
                  title={MS.FEATURE_MAP && MS.FEATURE_MAP[f.feature] ? `Xem chi tiết: ${f.feature}` : ''}
                >
                  {f.feature}
                  {MS.FEATURE_MAP && MS.FEATURE_MAP[f.feature] && (
                    <i className="ti ti-arrow-up-right" style={{ fontSize:'9px', marginLeft:'3px', opacity:.5, color:'var(--teal-5)' }}/>
                  )}
                </button>
                {f.value != null && (
                  <span className="top-feat-val">
                    {typeof f.value === 'number' ? f.value.toFixed(3) : f.value}
                  </span>
                )}
                <span className="top-feat-gain">gain {f.importance}</span>
              </div>
            ))}
            <div style={{
              marginTop: '8px', padding: '6px 8px',
              background: 'color-mix(in srgb, var(--teal-5) 6%, var(--surface))',
              border: '1px solid color-mix(in srgb, var(--teal-5) 20%, var(--border))',
              borderRadius: 'var(--r-sm)',
              fontFamily: 'var(--ff-body)', fontSize: '10.5px', color: 'var(--ink-4)',
              display: 'flex', alignItems: 'center', gap: '5px',
            }}>
              <i className="ti ti-info-circle" style={{ color:'var(--teal-5)', fontSize:'11px' }}/>
              Nhấn vào tên feature để xem giải thích chi tiết
            </div>
          </div>
        )}
      </div>
    );
  }

  const TREND_METRICS = {
    stress_probability: { label:'Stress score', unit:'%', color:'#0D9488', fmt:v => `${(v * 100).toFixed(1)}%` },
    salinity_psu:       { label:'Salinity',     unit:'PSU', color:'#D97706', fmt:v => `${v.toFixed(2)} PSU` },
    ndvi:               { label:'NDVI',         unit:'',    color:'#16A34A', fmt:v => v.toFixed(3) },
  };

  function TrendChart({ series, metric, height = 150 }) {
    const meta = TREND_METRICS[metric];
    const W = 560, H = height, pad = { l:38, r:16, t:14, b:28 };
    const plotW = W - pad.l - pad.r;
    const plotH = H - pad.t - pad.b;
    const values = series.flatMap(s => s.points.map(p => p[metric]).filter(v => typeof v === 'number' && !Number.isNaN(v)));
    if (!values.length) return <div className="trend-empty">Chưa có dữ liệu xu hướng</div>;

    let min = Math.min(...values);
    let max = Math.max(...values);
    if (metric === 'stress_probability') { min = 0; max = Math.max(.2, max); }
    if (Math.abs(max - min) < 1e-9) { min -= 1; max += 1; }
    const xFor = (i, n) => pad.l + (n <= 1 ? plotW / 2 : (i / (n - 1)) * plotW);
    const yFor = v => pad.t + (1 - ((v - min) / (max - min))) * plotH;
    const palette = ['#0D9488', '#D97706', '#2563EB', '#7C3AED', '#DC2626'];

    return (
      <svg className="trend-chart" viewBox={`0 0 ${W} ${H}`} role="img">
        {[0, .5, 1].map(t => {
          const y = pad.t + t * plotH;
          const val = max - t * (max - min);
          return (
            <g key={t}>
              <line x1={pad.l} x2={W - pad.r} y1={y} y2={y} className="trend-grid"/>
              <text x={pad.l - 8} y={y + 3} textAnchor="end" className="trend-axis">
                {metric === 'stress_probability' ? `${Math.round(val * 100)}%` : val.toFixed(metric === 'ndvi' ? 2 : 1)}
              </text>
            </g>
          );
        })}
        {series.map((s, si) => {
          const pts = s.points.filter(p => typeof p[metric] === 'number' && !Number.isNaN(p[metric]));
          const path = pts.map((p, i) => `${i ? 'L' : 'M'} ${xFor(i, pts.length).toFixed(2)} ${yFor(p[metric]).toFixed(2)}`).join(' ');
          const color = series.length === 1 ? meta.color : palette[si % palette.length];
          return (
            <g key={s.station_id}>
              <path d={path} className="trend-line" style={{ stroke:color }}/>
              {pts.map((p, i) => (i === pts.length - 1 || i === 0) && (
                <circle key={`${s.station_id}-${p.date}`} cx={xFor(i, pts.length)} cy={yFor(p[metric])} r="3.2" fill={color}/>
              ))}
            </g>
          );
        })}
        <text x={pad.l} y={H - 8} className="trend-axis">{series[0]?.points[0]?.date || ''}</text>
        <text x={W - pad.r} y={H - 8} textAnchor="end" className="trend-axis">
          {series[0]?.points[series[0].points.length - 1]?.date || ''}
        </text>
      </svg>
    );
  }

  function TrendSummary({ series, metric }) {
    const meta = TREND_METRICS[metric];
    const points = series[0]?.points || [];
    const first = points.find(p => typeof p[metric] === 'number');
    const last = [...points].reverse().find(p => typeof p[metric] === 'number');
    if (!first || !last) return null;
    const delta = last[metric] - first[metric];
    const worse = metric === 'ndvi' ? delta < 0 : delta > 0;
    const label = Math.abs(delta) < 1e-6 ? 'ổn định' : worse ? 'xấu đi' : 'tốt lên';
    return (
      <div className={`trend-summary ${worse ? 'bad' : 'good'}`}>
        <i className={`ti ${worse ? 'ti-trending-up' : 'ti-trending-down'} ti-sm`}/>
        {meta.fmt(first[metric])} → {meta.fmt(last[metric])} · {label}
      </div>
    );
  }

  function TrendPanel({ station, date, onShowToast }) {
    const [days, setDays] = useState(30);
    const [scope, setScope] = useState('station');
    const [metric, setMetric] = useState('stress_probability');
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
      if (!date || (scope === 'station' && !station)) return;
      let cancelled = false;
      async function loadTrend() {
        setLoading(true);
        try {
          const sid = scope === 'station' ? `&station_id=${encodeURIComponent(station)}` : '';
          const d = await MS.api.get(`/trends?date=${encodeURIComponent(date)}&days=${days}${sid}`);
          if (!cancelled) setData(d);
        } catch (e) {
          if (!cancelled && onShowToast) onShowToast(`Lỗi tải xu hướng: ${e.message}`, 'error');
        } finally {
          if (!cancelled) setLoading(false);
        }
      }
      loadTrend();
      return () => { cancelled = true; };
    }, [station, date, days, scope]);

    const series = data?.series || [];

    return (
      <div className="card trend-card">
        <div className="card-title trend-title">
          <i className="ti ti-chart-line ti-sm" style={{ color:'var(--teal-5)' }}/>
          Xu hướng nhiều ngày / nhiều trạm
          {loading && <span className="trend-loading">Đang tải...</span>}
        </div>
        <div className="trend-toolbar">
          <div className="trend-seg">
            {[7, 30, 90].map(n => (
              <button key={n} className={days === n ? 'active' : ''} onClick={() => setDays(n)}>{n} ngày</button>
            ))}
          </div>
          <div className="trend-seg">
            <button className={scope === 'station' ? 'active' : ''} onClick={() => setScope('station')}>Một trạm</button>
            <button className={scope === 'all' ? 'active' : ''} onClick={() => setScope('all')}>5 trạm</button>
          </div>
        </div>

        {scope === 'station' ? (
          <div className="trend-grid-cards">
            {Object.keys(TREND_METRICS).map(m => (
              <div key={m} className="trend-mini">
                <div className="trend-mini-head">
                  <span>{TREND_METRICS[m].label}</span>
                  <TrendSummary series={series} metric={m}/>
                </div>
                <TrendChart series={series} metric={m} height={122}/>
              </div>
            ))}
          </div>
        ) : (
          <>
            <div className="trend-metric-tabs">
              {Object.entries(TREND_METRICS).map(([k, m]) => (
                <button key={k} className={metric === k ? 'active' : ''} onClick={() => setMetric(k)}>{m.label}</button>
              ))}
            </div>
            <TrendChart series={series} metric={metric} height={176}/>
            <div className="trend-legend">
              {series.map((s, i) => (
                <span key={s.station_id}><i style={{ background:['#0D9488', '#D97706', '#2563EB', '#7C3AED', '#DC2626'][i % 5] }}/>{s.station_name}</span>
              ))}
            </div>
          </>
        )}
      </div>
    );
  }

  /* ── Center Panel ── */
  function PredictionPanel({ stations, selectedStation, onResult, onShowToast, onSelectStation }) {
    const DEMO_DATE = '2020-03-15';
    const [station, setStation]   = useState('');
    const [date,    setDate]      = useState(DEMO_DATE);
    const [features, setFeatures] = useState({});
    const [result,  setResult]    = useState(null);
    const [loading, setLoading]   = useState(false);
    const [loadingD, setLoadingD] = useState(false);
    const [acc, setAcc] = useState({ veg:true, sal:true, climate:false, soil:false });
    const resultRef = useRef(null);

    useEffect(() => { onResult && onResult(result, station); }, [result]);

    useEffect(() => {
      if (stations.length && !station) setStation(stations[0].station_id);
    }, [stations]);

    useEffect(() => {
      if (!selectedStation || selectedStation === station) return;
      setStation(selectedStation);
      setResult(null);
    }, [selectedStation]);

    useEffect(() => {
      if (!station || !date) return;
      loadDataSilent();
    }, [station, date]);

    const setFeat = (k, v) => setFeatures(prev => ({ ...prev, [k]: v }));
    const toggleAcc = k => setAcc(prev => ({ ...prev, [k]: !prev[k] }));

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

    async function loadDataSilent() {
      if (!station || !date) return;
      setLoadingD(true);
      await fetchFeatures(station, date);
      setLoadingD(false);
    }

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

    const stationInfo = stations.find(s => s.station_id === station);

    return (
      <div className="panel panel-center">
        <div className="content-breadcrumb">
          <i className="ti ti-seeding ti-sm"/>
          <span>ĐBSCL</span>
          <i className="ti ti-chevron-right ti-xs"/>
          <span>Bến Tre</span>
          <i className="ti ti-chevron-right ti-xs"/>
          <strong>crop-stress</strong>
        </div>

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
                    onChange={e => {
                      const val = e.target.value;
                      setStation(val);
                      setResult(null);
                      if (onSelectStation) onSelectStation(val);
                    }}>
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

        <TrendPanel station={station} date={date} onShowToast={onShowToast}/>

        {/* Feature accordion */}
        <div className="card" style={{ padding:'12px 14px' }}>
          <div className="card-title">
            <i className="ti ti-adjustments-horizontal ti-sm" style={{ color:'var(--teal-5)' }}/>
            Thông số đầu vào — 46 features
            <span style={{
              marginLeft: 'auto',
              fontFamily: 'var(--ff-body)', fontSize: '10px', color: 'var(--teal-5)',
              display: 'flex', alignItems: 'center', gap: '3px',
              fontWeight: 400, opacity: .8,
            }}>
              <i className="ti ti-arrow-up-right" style={{ fontSize:'10px' }}/> Nhấn tên để xem chi tiết
            </span>
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
          <ResultCard
            result={result}
            stationInfo={stationInfo}
            date={date}
            features={features}
            onShowToast={onShowToast}
          />
        </div>
      </div>
    );
  }

  MS.PredictionPanel = PredictionPanel;
  MS.CircularGauge  = CircularGauge;
}());
