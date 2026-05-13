/* ── MapPage + AboutPage ── */
(function () {
  const { useState, useEffect, useRef } = React;

  /* ─────────────────────────────────────────────
     MAP PAGE — full-screen Leaflet + station stats
  ───────────────────────────────────────────── */
  function FullMap({ stations, selected, onSelect }) {
    const divRef = useRef(null);
    const mapRef = useRef(null);
    const mkRef  = useRef({});

    useEffect(() => {
      if (!divRef.current || mapRef.current) return;
      const map = L.map(divRef.current, {
        center: [10.12, 106.55], zoom: 11,
        zoomControl: true, attributionControl: false,
      });
      L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
        subdomains: 'abcd', maxZoom: 19,
      }).addTo(map);
      L.control.attribution({ prefix: false })
        .addAttribution('© <a href="https://www.openstreetmap.org/copyright">OSM</a> © <a href="https://carto.com">CARTO</a>')
        .addTo(map);
      mapRef.current = map;
      return () => { if (mapRef.current) { mapRef.current.remove(); mapRef.current = null; } };
    }, []);

    useEffect(() => {
      const map = mapRef.current;
      if (!map || !stations.length) return;
      Object.values(mkRef.current).forEach(m => m.remove());
      mkRef.current = {};

      stations.forEach(s => {
        const rate = s.stress_rate_30d ?? 0.1;
        const col  = rate >= 0.15 ? '#C82020' : rate >= 0.05 ? '#C48020' : '#0FA860';
        const isSel = s.station_id === selected;

        const mk = L.circleMarker([s.lat, s.lon], {
          radius: isSel ? 18 : 14,
          fillColor: col, color: isSel ? '#1B3A0E' : 'white',
          weight: isSel ? 3 : 2, fillOpacity: isSel ? .95 : .85,
        }).addTo(map);

        mk.bindPopup(
          `<div style="font-family:Nunito,sans-serif;min-width:180px">
             <div style="font-size:15px;font-weight:800;color:#1B3A0E;margin-bottom:8px">
               <i class="ti ti-building-broadcast-tower" style="font-size:13px;margin-right:4px;opacity:.6"></i>${s.name}
             </div>
             <table style="width:100%;font-size:12px;border-collapse:collapse">
               <tr><td style="color:#587A40;padding:3px 0">Stress 30d</td>
                   <td style="text-align:right;font-weight:700;color:${col}">${(rate*100).toFixed(1)}%</td></tr>
               <tr><td style="color:#587A40;padding:3px 0">Stress tổng</td>
                   <td style="text-align:right;font-weight:700;color:#2C6A1A">${((s.stress_rate_total??0.1)*100).toFixed(1)}%</td></tr>
               <tr><td style="color:#587A40;padding:3px 0">Cửa biển</td>
                   <td style="text-align:right;font-family:JetBrains Mono,monospace;color:#1A8898">${s.distance_to_estuary_km} km</td></tr>
               <tr><td style="color:#587A40;padding:3px 0">Tọa độ</td>
                   <td style="text-align:right;font-family:JetBrains Mono,monospace;font-size:10.5px;color:#8A7040">${s.lat.toFixed(4)}, ${s.lon.toFixed(4)}</td></tr>
             </table>
           </div>`,
          { maxWidth: 240 }
        );

        if (isSel) mk.openPopup();
        mk.on('click', () => { onSelect(s.station_id); mk.openPopup(); });
        mk.on('mouseover', function() {
          if (s.station_id !== selected) this.setStyle({ radius: 16, fillOpacity: .92 });
        });
        mk.on('mouseout', function() {
          if (s.station_id !== selected) this.setStyle({ radius: 14, fillOpacity: .85 });
        });
        mkRef.current[s.station_id] = mk;
      });
    }, [stations, selected]);

    return <div ref={divRef} style={{ width:'100%', height:'100%' }}/>;
  }

  function MapPage({ stations, selected, onSelect }) {
    const sel = stations.find(s => s.station_id === selected);

    return (
      <div style={{ display:'flex', height:'calc(100vh - 50px)', overflow:'hidden' }}>
        {/* Sidebar */}
        <div style={{
          width:'280px', flexShrink:0,
          background:'var(--surface-2)', borderRight:'1px solid var(--border)',
          overflowY:'auto', padding:'16px 14px',
        }}>
          <div className="sec-title">
            <i className="ti ti-map-2 ti-md" style={{ color:'var(--teal-5)' }}/>
            Bản đồ quan trắc
            <span className="sec-title-badge">{stations.length} trạm</span>
          </div>

          {/* Legend */}
          <div style={{ display:'flex', flexDirection:'column', gap:'6px', marginBottom:'14px' }}>
            {[['#0FA860','Thấp (< 5%)', 'Nguy cơ thấp, cây khỏe'],
              ['#C48020','Vừa (5–15%)', 'Theo dõi thường xuyên'],
              ['#C82020','Cao (> 15%)', 'Cần can thiệp gấp']].map(([c,l,d]) => (
              <div key={l} style={{ display:'flex', alignItems:'center', gap:'8px' }}>
                <div style={{ width:'10px', height:'10px', borderRadius:'50%', background:c, flexShrink:0 }}/>
                <div>
                  <div style={{ fontSize:'11.5px', fontWeight:700, color:'var(--ink-2)' }}>{l}</div>
                  <div style={{ fontSize:'10px', color:'var(--ink-4)', fontFamily:'var(--ff-body)' }}>{d}</div>
                </div>
              </div>
            ))}
          </div>

          {/* Station list */}
          {stations.map(s => {
            const rate = s.stress_rate_30d ?? 0.1;
            const col  = rate >= 0.15 ? '#C82020' : rate >= 0.05 ? '#C48020' : '#0FA860';
            const isSel = s.station_id === selected;
            return (
              <div
                key={s.station_id}
                className={`stn-card${isSel ? ' sel' : ''}`}
                style={{ '--stn-clr': col }}
                onClick={() => onSelect(s.station_id)}
              >
                <div className="stn-dot" style={{ background:col }}/>
                <div className="stn-info">
                  <div className="stn-name">{s.name}</div>
                  <div className="stn-meta">{s.distance_to_estuary_km} km · cửa biển</div>
                </div>
                <span className="stn-rate" style={{
                  background:`color-mix(in srgb, ${col} 12%, white)`,
                  color:col, border:`1px solid color-mix(in srgb, ${col} 30%, white)`,
                }}>
                  {(rate*100).toFixed(0)}%
                </span>
              </div>
            );
          })}

          {/* Selected station detail */}
          {sel && (
            <div style={{
              marginTop:'14px', padding:'12px', borderRadius:'var(--r-md)',
              background:'var(--surface)', border:'1px solid var(--border)',
              boxShadow:'var(--sh-sm)',
            }}>
              <div style={{ fontFamily:'var(--ff-heading)', fontSize:'14px', fontWeight:700, color:'var(--ink-1)', marginBottom:'10px', display:'flex', alignItems:'center', gap:'6px' }}>
                <i className="ti ti-info-circle" style={{ color:'var(--teal-5)', fontSize:'14px' }}/>
                {sel.name}
              </div>
              {[
                ['Stress 30 ngày', `${((sel.stress_rate_30d??0.1)*100).toFixed(1)}%`, sel.stress_rate_30d>=0.15?'var(--danger-5)':sel.stress_rate_30d>=0.05?'var(--warn-5)':'var(--safe-5)'],
                ['Stress tổng',   `${((sel.stress_rate_total??0.1)*100).toFixed(1)}%`, 'var(--ink-2)'],
                ['Cửa biển',       `${sel.distance_to_estuary_km} km`, 'var(--teal-5)'],
                ['Vĩ độ / Kinh độ', `${sel.lat.toFixed(4)}°N, ${sel.lon.toFixed(4)}°E`, 'var(--ink-3)'],
              ].map(([lbl,val,clr]) => (
                <div key={lbl} style={{ display:'flex', justifyContent:'space-between', padding:'5px 0', borderBottom:'1px solid var(--border)', fontSize:'12px' }}>
                  <span style={{ color:'var(--ink-4)', fontFamily:'var(--ff-body)' }}>{lbl}</span>
                  <span style={{ color:clr, fontFamily:'var(--ff-mono)', fontWeight:700 }}>{val}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Full map */}
        <div style={{ flex:1, position:'relative' }}>
          <FullMap stations={stations} selected={selected} onSelect={onSelect}/>

          {/* Floating info box */}
          <div style={{
            position:'absolute', top:'14px', right:'14px', zIndex:800,
            background:'rgba(244,246,240,.92)', backdropFilter:'blur(10px)',
            border:'1px solid var(--border-md)', borderRadius:'var(--r-md)',
            padding:'11px 14px', boxShadow:'var(--sh-sm)',
            fontFamily:'var(--ff-body)', fontSize:'12px', color:'var(--ink-3)',
            maxWidth:'200px',
          }}>
            <div style={{ fontWeight:800, color:'var(--ink-1)', marginBottom:'5px', display:'flex', alignItems:'center', gap:'5px' }}>
              <i className="ti ti-seeding" style={{ color:'var(--green-5)' }}/>
              Bến Tre, ĐBSCL
            </div>
            <div>5 trạm quan trắc</div>
            <div>Giai đoạn 2015–2025</div>
            <div style={{ marginTop:'6px', paddingTop:'6px', borderTop:'1px solid var(--border)', color:'var(--teal-5)', fontWeight:700 }}>
              <i className="ti ti-click" style={{ fontSize:'11px', marginRight:'3px' }}/>
              Click marker để xem chi tiết
            </div>
          </div>
        </div>
      </div>
    );
  }

  /* ─────────────────────────────────────────────
     ABOUT PAGE — model perf, tech stack, data
  ───────────────────────────────────────────── */
  const METRICS = [
    { label:'PR-AUC',    value:'0.974', icon:'ti-chart-area',        color:'var(--teal-5)',   desc:'Precision-Recall, phân lớp mất cân bằng' },
    { label:'F2-Score',  value:'0.925', icon:'ti-target',            color:'var(--safe-5)',   desc:'Ưu tiên recall (β=2) cho cây trồng' },
    { label:'Recall',    value:'0.939', icon:'ti-eye-check',         color:'var(--green-5)',  desc:'Phát hiện 93.9% stress thật' },
    { label:'Precision', value:'0.874', icon:'ti-crosshair',         color:'var(--gold-6)',   desc:'87.4% dự báo dương tính chính xác' },
  ];

  const TECH_STACK = [
    { name:'XGBoost',      icon:'ti-circuit-cell',      role:'Mô hình phân loại chính (Optuna-tuned)',    color:'#E8683A' },
    { name:'PrefixSpan',   icon:'ti-timeline',          role:'Sequential Pattern Mining, 14d lookback',  color:'#7C5CBF' },
    { name:'FastAPI',      icon:'ti-api',               role:'REST API backend, Python 3.10+',           color:'#09A4B8' },
    { name:'React 18',     icon:'ti-brand-react',       role:'SPA frontend, CDN + Babel standalone',     color:'#58C4DC' },
    { name:'SQLite',       icon:'ti-database',          role:'Prediction history, CRUD local',           color:'#5D8EBF' },
    { name:'APScheduler',  icon:'ti-clock-hour-4',      role:'Daily 06:00 pipeline trigger',             color:'#2F9E44' },
    { name:'Leaflet',      icon:'ti-map-2',             role:'Interactive map, CartoDB Voyager tiles',   color:'#5D9C00' },
    { name:'Open-Meteo',   icon:'ti-cloud-rain',        role:'ERA5-Land climate reanalysis data',        color:'#1A8898' },
  ];

  const DATA_SOURCES = [
    { name:'NASA MODIS', desc:'NDVI (MOD13Q1) + LST (MOD11A1) · 250m/1km resolution', icon:'ti-satellite', color:'#5D8EBF' },
    { name:'Open-Meteo', desc:'ERA5-Land: nhiệt độ, mưa, ET0, bức xạ, gió, độ ẩm đất', icon:'ti-cloud-storm', color:'#1A8898' },
    { name:'Google Earth Engine', desc:'Trích xuất dữ liệu vệ tinh theo trạm & ngày', icon:'ti-brand-google', color:'#2F9E44' },
    { name:'Quan trắc địa phương', desc:'Salinity PSU 5 trạm Bến Tre · 2015–2025', icon:'ti-building-broadcast-tower', color:'#C48020' },
  ];

  const TOP_FEATURES = [
    { rank:1, name:'ndvi_tendency',         gain:245.1, desc:'Xu hướng thực vật' },
    { rank:2, name:'ndvi',                  gain:103.0, desc:'Chỉ số thực vật hiện tại' },
    { rank:3, name:'lat',                   gain: 92.2, desc:'Vĩ độ (proxy địa lý)' },
    { rank:4, name:'lon',                   gain: 80.0, desc:'Kinh độ (proxy địa lý)' },
    { rank:5, name:'ndvi_lag_1',            gain: 54.9, desc:'NDVI ngày trước' },
    { rank:6, name:'distance_to_estuary_km',gain: 53.8, desc:'Khoảng cách cửa biển' },
    { rank:7, name:'lst_ndvi_ratio',        gain: 38.3, desc:'Tỉ lệ nhiệt / thực vật' },
    { rank:8, name:'ndvi_lag_7',            gain: 37.4, desc:'Xu hướng tuần trước' },
    { rank:9, name:'day_of_year',           gain: 27.3, desc:'Chu kỳ mùa vụ' },
    {rank:10, name:'salinity_7d_median',    gain: 26.8, desc:'Mặn trung vị 7 ngày' },
  ];

  const maxGain = TOP_FEATURES[0].gain;

  function MetricCard({ metric }) {
    return (
      <div style={{
        background:'var(--surface)', border:'1px solid var(--border)',
        borderRadius:'var(--r-lg)', padding:'18px 20px',
        boxShadow:'var(--sh-sm)',
        display:'flex', flexDirection:'column', gap:'8px',
        transition:'all .2s ease',
      }}
      onMouseEnter={e => { e.currentTarget.style.transform='translateY(-1px)'; e.currentTarget.style.boxShadow='var(--sh-md)'; }}
      onMouseLeave={e => { e.currentTarget.style.transform=''; e.currentTarget.style.boxShadow='var(--sh-sm)'; }}
      >
        <div style={{ display:'flex', alignItems:'center', gap:'9px' }}>
          <div style={{
            width:'34px', height:'34px', borderRadius:'var(--r-sm)',
            background:`color-mix(in srgb, ${metric.color} 14%, var(--surface))`,
            border:`1.5px solid color-mix(in srgb, ${metric.color} 35%, var(--border))`,
            display:'flex', alignItems:'center', justifyContent:'center',
          }}>
            <i className={`ti ${metric.icon}`} style={{ fontSize:'16px', color:metric.color }}/>
          </div>
          <span style={{ fontFamily:'var(--ff-mono)', fontSize:'11px', fontWeight:700, color:'var(--ink-4)', textTransform:'uppercase', letterSpacing:'.08em' }}>{metric.label}</span>
        </div>
        <div style={{ fontFamily:'var(--ff-mono)', fontSize:'32px', fontWeight:700, color:metric.color, lineHeight:1 }}>{metric.value}</div>
        <div style={{ fontFamily:'var(--ff-body)', fontSize:'11.5px', color:'var(--ink-4)' }}>{metric.desc}</div>
      </div>
    );
  }

  function AboutPage() {
    return (
      <div style={{ overflowY:'auto', height:'calc(100vh - 50px)' }}>

        {/* Hero banner */}
        <div style={{
          position:'relative', height:'220px', overflow:'hidden',
          display:'flex', alignItems:'center',
        }}>
          <img
            src="./assets/hero-rice.jpg"
            alt="Rice field"
            style={{
              position:'absolute', inset:0, width:'100%', height:'100%',
              objectFit:'cover', objectPosition:'center',
              filter:'brightness(.55) saturate(.85)',
            }}
            onError={e => { e.target.style.display='none'; }}
          />
          <div style={{
            position:'absolute', inset:0,
            background:'linear-gradient(90deg, rgba(10,30,10,.75) 0%, rgba(10,30,10,.3) 60%, transparent 100%)',
          }}/>
          <div style={{ position:'relative', padding:'0 48px', maxWidth:'700px' }}>
            <div style={{ fontFamily:'var(--ff-display)', fontSize:'32px', color:'#E8C870', textShadow:'0 2px 16px rgba(0,0,0,.5)', lineHeight:1.2, marginBottom:'8px' }}>
              SaltySeq
            </div>
            <div style={{ fontFamily:'var(--ff-heading)', fontSize:'17px', color:'rgba(220,240,200,.9)', marginBottom:'12px', fontStyle:'italic' }}>
              Dự báo căng thẳng cây trồng do xâm nhập mặn — Bến Tre, ĐBSCL
            </div>
            <div style={{ display:'flex', gap:'10px', flexWrap:'wrap' }}>
              {['CS313 · UIT 2025–2026','XGBoost + PrefixSpan','20,090 điểm dữ liệu','5 trạm quan trắc'].map(t => (
                <span key={t} style={{
                  fontFamily:'var(--ff-mono)', fontSize:'10.5px', fontWeight:700,
                  padding:'3px 10px', borderRadius:'var(--r-full)',
                  background:'rgba(255,255,255,.12)', color:'rgba(220,240,200,.9)',
                  border:'1px solid rgba(255,255,255,.2)',
                }}>{t}</span>
              ))}
            </div>
          </div>
        </div>

        <div style={{ padding:'28px 36px', maxWidth:'1100px', margin:'0 auto' }}>

          {/* Pipeline overview */}
          <div style={{ marginBottom:'32px' }}>
            <div style={{ fontFamily:'var(--ff-heading)', fontSize:'20px', fontWeight:700, color:'var(--ink-1)', marginBottom:'14px', display:'flex', alignItems:'center', gap:'8px' }}>
              <i className="ti ti-route" style={{ color:'var(--teal-5)' }}/> Sơ đồ pipeline
            </div>
            <div className="pipeline-flow">
              {[
                ['Nguồn dữ liệu', 'MODIS, Open-Meteo, GEE, quan trắc mặn', 'ti-database'],
                ['Feature engineering', '46 đặc trưng theo trạm/ngày', 'ti-adjustments-horizontal'],
                ['XGBoost', 'Dự báo xác suất stress cây trồng', 'ti-chart-histogram'],
                ['PrefixSpan', 'Tìm chuỗi cảnh báo trong 14 ngày', 'ti-timeline'],
                ['Khuyến nghị', 'Ưu tiên hành động theo mức rủi ro', 'ti-clipboard-list'],
              ].map(([title, desc, icon], i, arr) => (
                <React.Fragment key={title}>
                  <div className="pipeline-step">
                    <div className="pipeline-icon"><i className={`ti ${icon}`} /></div>
                    <div className="pipeline-title">{title}</div>
                    <div className="pipeline-desc">{desc}</div>
                  </div>
                  {i < arr.length - 1 && <div className="pipeline-arrow"><i className="ti ti-arrow-right" /></div>}
                </React.Fragment>
              ))}
            </div>
          </div>

          {/* Model metrics */}
          <div style={{ marginBottom:'32px' }}>
            <div style={{ fontFamily:'var(--ff-heading)', fontSize:'20px', fontWeight:700, color:'var(--ink-1)', marginBottom:'16px', display:'flex', alignItems:'center', gap:'8px' }}>
              <i className="ti ti-chart-bar" style={{ color:'var(--green-5)' }}/> Hiệu năng mô hình
              <span style={{ fontFamily:'var(--ff-mono)', fontSize:'10px', padding:'2px 8px', background:'var(--safe-lt)', color:'var(--safe-5)', border:'1px solid var(--safe-bd)', borderRadius:'var(--r-full)' }}>Optuna-tuned XGBoost</span>
            </div>
            <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:'14px' }}>
              {METRICS.map(m => <MetricCard key={m.label} metric={m}/>)}
            </div>
            <div style={{
              marginTop:'12px', padding:'11px 14px',
              background:'var(--surface)', border:'1px solid var(--border)',
              borderRadius:'var(--r-md)', fontFamily:'var(--ff-body)', fontSize:'12px', color:'var(--ink-3)',
              display:'flex', gap:'20px', flexWrap:'wrap',
            }}>
              <span><strong style={{ color:'var(--ink-2)' }}>Ngưỡng rủi ro:</strong> Cảnh báo ≥5% · Nguy hiểm ≥15%</span>
              <span><strong style={{ color:'var(--ink-2)' }}>Scale pos weight:</strong> 8.946 (class imbalance ~10% positive)</span>
              <span><strong style={{ color:'var(--ink-2)' }}>Train/Test split:</strong> ≤ 2022-12-31 / 2023-01-01 → 2025</span>
              <span><strong style={{ color:'var(--ink-2)' }}>Features:</strong> 46 chiều đa nguồn</span>
            </div>
          </div>

          {/* Top features */}
          <div style={{ marginBottom:'32px' }}>
            <div style={{ fontFamily:'var(--ff-heading)', fontSize:'20px', fontWeight:700, color:'var(--ink-1)', marginBottom:'16px', display:'flex', alignItems:'center', gap:'8px' }}>
              <i className="ti ti-trophy" style={{ color:'var(--gold-6)' }}/> Top 10 Feature Importance
              <span style={{ fontFamily:'var(--ff-mono)', fontSize:'10px', padding:'2px 8px', background:'var(--gold-lt)', color:'var(--gold)', border:'1px solid var(--gold-bd)', borderRadius:'var(--r-full)' }}>XGBoost gain score</span>
            </div>
            <div style={{
              background:'var(--surface)', border:'1px solid var(--border)',
              borderRadius:'var(--r-lg)', padding:'16px 20px', boxShadow:'var(--sh-sm)',
            }}>
              {TOP_FEATURES.map(f => {
                const hasEntry = MS.FEATURE_MAP && MS.FEATURE_MAP[f.name];
                return (
                  <div
                    key={f.rank}
                    className="top-feat"
                    style={{
                      display:'flex', alignItems:'center', gap:'12px',
                      padding:'7px 0', borderBottom:'1px solid var(--border)',
                      cursor: hasEntry ? 'pointer' : 'default',
                      borderRadius:'var(--r-sm)',
                      transition:'background .15s',
                    }}
                    onClick={() => hasEntry && MS.navigateToFeature && MS.navigateToFeature(f.name)}
                    onMouseEnter={e => { if (hasEntry) e.currentTarget.style.background='var(--surface-hover)'; }}
                    onMouseLeave={e => { e.currentTarget.style.background=''; }}
                    title={hasEntry ? `Xem chi tiết: ${f.name} →` : ''}
                  >
                    <span style={{ fontFamily:'var(--ff-mono)', fontSize:'11px', color:'var(--ink-4)', width:'20px', textAlign:'right' }}>#{f.rank}</span>
                    <div style={{ flex:1, minWidth:0 }}>
                      <div style={{ display:'flex', alignItems:'center', gap:'5px' }}>
                        <span style={{ fontFamily:'var(--ff-mono)', fontSize:'12px', color: hasEntry ? 'var(--teal-5)' : 'var(--ink-2)', fontWeight:600, transition:'color .15s' }}>{f.name}</span>
                        {hasEntry && (
                          <i className="ti ti-arrow-up-right" style={{ fontSize:'10px', color:'var(--teal-5)', opacity:.6 }}/>
                        )}
                      </div>
                      <div style={{ fontFamily:'var(--ff-body)', fontSize:'10.5px', color:'var(--ink-4)' }}>{f.desc}</div>
                    </div>
                    <div style={{ width:'220px' }}>
                      <div style={{ height:'6px', background:'var(--surface-3)', borderRadius:'3px', overflow:'hidden', border:'1px solid var(--border)', marginBottom:'3px' }}>
                        <div style={{
                          height:'100%', borderRadius:'3px',
                          width:`${(f.gain/maxGain*100).toFixed(1)}%`,
                          background:'linear-gradient(90deg, var(--green-5) 0%, var(--teal-5) 100%)',
                          transition:'width 1.2s ease',
                        }}/>
                      </div>
                    </div>
                    <span style={{ fontFamily:'var(--ff-mono)', fontSize:'11px', color:'var(--gold-6)', fontWeight:700, width:'44px', textAlign:'right' }}>{f.gain}</span>
                  </div>
                );
              })}
            </div>
            <div style={{
              marginTop:'8px', padding:'7px 12px',
              background:'color-mix(in srgb, var(--teal-5) 6%, var(--surface))',
              border:'1px solid color-mix(in srgb, var(--teal-5) 20%, var(--border))',
              borderRadius:'var(--r-sm)',
              fontFamily:'var(--ff-body)', fontSize:'11px', color:'var(--ink-4)',
              display:'flex', alignItems:'center', gap:'5px',
            }}>
              <i className="ti ti-info-circle" style={{ color:'var(--teal-5)', fontSize:'12px' }}/>
              Nhấn vào tên feature để xem giải thích chi tiết trong trang Đặc trưng
            </div>
          </div>

          {/* 2-col: tech stack + data sources */}
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'24px', marginBottom:'32px' }}>

            {/* Tech stack */}
            <div>
              <div style={{ fontFamily:'var(--ff-heading)', fontSize:'20px', fontWeight:700, color:'var(--ink-1)', marginBottom:'14px', display:'flex', alignItems:'center', gap:'8px' }}>
                <i className="ti ti-layers-intersect" style={{ color:'var(--teal-5)' }}/> Tech Stack
              </div>
              <div style={{
                background:'var(--surface)', border:'1px solid var(--border)',
                borderRadius:'var(--r-lg)', overflow:'hidden', boxShadow:'var(--sh-sm)',
              }}>
                {TECH_STACK.map((t, i) => (
                  <div key={t.name} style={{
                    display:'flex', alignItems:'center', gap:'12px', padding:'11px 16px',
                    borderBottom: i < TECH_STACK.length-1 ? '1px solid var(--border)' : 'none',
                    transition:'background .15s',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background='var(--surface-hover)'}
                  onMouseLeave={e => e.currentTarget.style.background=''}
                  >
                    <div style={{
                      width:'32px', height:'32px', borderRadius:'var(--r-sm)', flexShrink:0,
                      background:`color-mix(in srgb, ${t.color} 14%, var(--surface))`,
                      border:`1.5px solid color-mix(in srgb, ${t.color} 30%, var(--border))`,
                      display:'flex', alignItems:'center', justifyContent:'center',
                    }}>
                      <i className={`ti ${t.icon}`} style={{ fontSize:'15px', color:t.color }}/>
                    </div>
                    <div style={{ flex:1, minWidth:0 }}>
                      <div style={{ fontFamily:'var(--ff-mono)', fontSize:'12.5px', fontWeight:700, color:'var(--ink-1)' }}>{t.name}</div>
                      <div style={{ fontFamily:'var(--ff-body)', fontSize:'11px', color:'var(--ink-4)', marginTop:'1px' }}>{t.role}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Data sources */}
            <div>
              <div style={{ fontFamily:'var(--ff-heading)', fontSize:'20px', fontWeight:700, color:'var(--ink-1)', marginBottom:'14px', display:'flex', alignItems:'center', gap:'8px' }}>
                <i className="ti ti-database" style={{ color:'var(--gold-6)' }}/> Nguồn dữ liệu
              </div>
              <div style={{ display:'flex', flexDirection:'column', gap:'10px' }}>
                {DATA_SOURCES.map(d => (
                  <div key={d.name} style={{
                    background:'var(--surface)', border:'1px solid var(--border)',
                    borderRadius:'var(--r-md)', padding:'13px 16px', boxShadow:'var(--sh-xs)',
                    display:'flex', gap:'12px', alignItems:'flex-start',
                    transition:'all .2s ease',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.transform='translateY(-1px)'; e.currentTarget.style.boxShadow='var(--sh-sm)'; }}
                  onMouseLeave={e => { e.currentTarget.style.transform=''; e.currentTarget.style.boxShadow='var(--sh-xs)'; }}
                  >
                    <div style={{
                      width:'36px', height:'36px', borderRadius:'var(--r-sm)', flexShrink:0,
                      background:`color-mix(in srgb, ${d.color} 14%, var(--surface))`,
                      border:`1.5px solid color-mix(in srgb, ${d.color} 35%, var(--border))`,
                      display:'flex', alignItems:'center', justifyContent:'center',
                    }}>
                      <i className={`ti ${d.icon}`} style={{ fontSize:'17px', color:d.color }}/>
                    </div>
                    <div>
                      <div style={{ fontFamily:'var(--ff-mono)', fontSize:'12.5px', fontWeight:700, color:'var(--ink-1)', marginBottom:'3px' }}>{d.name}</div>
                      <div style={{ fontFamily:'var(--ff-body)', fontSize:'11.5px', color:'var(--ink-3)' }}>{d.desc}</div>
                    </div>
                  </div>
                ))}
              </div>

              {/* SPM summary */}
              <div style={{
                marginTop:'12px', padding:'14px 16px',
                background:'linear-gradient(135deg, color-mix(in srgb, var(--green-5) 8%, var(--surface)) 0%, var(--surface) 100%)',
                border:'1px solid var(--green-bd)', borderRadius:'var(--r-md)', boxShadow:'var(--sh-xs)',
              }}>
                <div style={{ fontFamily:'var(--ff-mono)', fontSize:'11px', fontWeight:700, color:'var(--green-5)', textTransform:'uppercase', letterSpacing:'.07em', marginBottom:'8px' }}>
                  <i className="ti ti-timeline" style={{ marginRight:'5px' }}/> PrefixSpan Results
                </div>
                {[['939','Patterns phổ biến tổng'],['41','Danger-ending patterns'],['152','Warning-ending patterns'],['14 ngày','Lookback window'],['3%','Min support']].map(([v,l]) => (
                  <div key={l} style={{ display:'flex', justifyContent:'space-between', padding:'4px 0', borderBottom:'1px solid var(--border)', fontSize:'12px' }}>
                    <span style={{ color:'var(--ink-4)', fontFamily:'var(--ff-body)' }}>{l}</span>
                    <span style={{ color:'var(--green-5)', fontFamily:'var(--ff-mono)', fontWeight:700 }}>{v}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Footer */}
          <div style={{
            textAlign:'center', padding:'20px', borderTop:'1px solid var(--border)',
            fontFamily:'var(--ff-body)', fontSize:'12px', color:'var(--ink-4)',
          }}>
            <div style={{ marginBottom:'6px', fontFamily:'var(--ff-display)', fontSize:'16px', color:'var(--ink-3)' }}>Mekong Sentinel · SaltySeq</div>
            CS313 · Đại học Công nghệ Thông tin (UIT) · Học kỳ 2, 2025–2026
          </div>
        </div>
      </div>
    );
  }

  MS.MapPage   = MapPage;
  MS.AboutPage = AboutPage;
}());
