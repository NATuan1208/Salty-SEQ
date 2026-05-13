/* ── Header + Toast ── */
(function () {
  const { useState } = React;

  /* Inline SVG rice stalk decoration */
  function RiceIcon({ size = 22, color = '#E8C870' }) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        {/* Stem */}
        <path d="M12 22 L12 8" stroke={color} strokeWidth="1.6" strokeLinecap="round"/>
        {/* Grains */}
        <ellipse cx="12" cy="7"  rx="2.2" ry="3.2" fill={color} opacity=".9"/>
        <ellipse cx="8.5" cy="9.5" rx="1.8" ry="2.8" fill={color} opacity=".75" transform="rotate(-20 8.5 9.5)"/>
        <ellipse cx="15.5" cy="9.5" rx="1.8" ry="2.8" fill={color} opacity=".75" transform="rotate(20 15.5 9.5)"/>
        <ellipse cx="6.5" cy="12.5" rx="1.5" ry="2.4" fill={color} opacity=".55" transform="rotate(-30 6.5 12.5)"/>
        <ellipse cx="17.5" cy="12.5" rx="1.5" ry="2.4" fill={color} opacity=".55" transform="rotate(30 17.5 12.5)"/>
      </svg>
    );
  }

  /* Wave decoration in header */
  function HeaderWave() {
    return (
      <svg
        style={{ position:'absolute', right:'160px', top:0, opacity:.08, pointerEvents:'none', height:'50px' }}
        viewBox="0 0 200 50"
        fill="none"
        preserveAspectRatio="xMidYMid meet"
      >
        <path d="M0 30 C20 18,40 42,60 30 C80 18,100 42,120 30 C140 18,160 42,180 30 C190 24,196 28,200 30" stroke="#4ADE80" strokeWidth="1.2" fill="none"/>
        <path d="M0 38 C20 26,40 50,60 38 C80 26,100 50,120 38 C140 26,160 50,180 38" stroke="#E8C870" strokeWidth=".8" fill="none"/>
      </svg>
    );
  }

  function Toast({ toast }) {
    if (!toast) return null;
    return (
      <div className={`toast ${toast.type}`} role="alert" aria-live="polite">
        <div className="toast-bar"/>
        <span>{toast.message}</span>
      </div>
    );
  }

  /* ── NAV ITEMS: thêm 'features' giữa 'predict' và 'map' ── */
  const NAV_ITEMS = [
    { id:'predict',  icon:'ti-chart-histogram', label:'Dự báo'        },
    { id:'features', icon:'ti-database-search', label:'Đặc trưng'     },
    { id:'map',      icon:'ti-map-2',           label:'Bản đồ'        },
    { id:'about',    icon:'ti-info-circle',      label:'Về dự án'     },
    { id: 'recommendations', label: 'Khuyến nghị', icon: 'ti-clipboard-list' }
  ];

  function Header({ pipeStatus, onTriggerPipeline, page, onSetPage }) {
    const [running, setRunning] = useState(false);
    const state   = pipeStatus?.status || 'never';
    const stateVI = { success:'Hoạt động', running:'Đang chạy', failed:'Lỗi', never:'Chờ' };
    const lastRun = pipeStatus?.last_run?.split('T')[0];

    async function handleRun() {
      setRunning(true);
      await onTriggerPipeline();
      setTimeout(() => setRunning(false), 3500);
    }

    return (
      <header className="hdr">
        {/* Decorative waves */}
        <HeaderWave/>

        {/* Logo */}
        <a href="/" className="hdr-logo" onClick={e => { e.preventDefault(); onSetPage('predict'); }}>
          <div className="logo-mark">
            <RiceIcon size={20} color="#E8C870"/>
          </div>
          <div>
            <div className="logo-text">Mekong Sentinel</div>
            <div className="logo-sub">SaltySeq · CS313 · UIT · 2025</div>
          </div>
        </a>

        {/* Nav */}
        <nav className="hdr-nav">
          {NAV_ITEMS.map(n => (
            <button
              key={n.id}
              className={`hdr-nav-item${page === n.id ? ' active' : ''}`}
              onClick={() => onSetPage(n.id)}
            >
              <i className={`ti ${n.icon} ti-sm`}/> {n.label}
            </button>
          ))}
        </nav>

        <div className="hdr-spacer"/>

        <div className="hdr-right">
          {/* Pipeline status */}
          <div className="pipe-pill">
            <div className={`sdot ${running ? 'running' : state}`}/>
            <span>Pipeline:&nbsp;
              <strong style={{ color:'#E8F8D0' }}>
                {running ? 'Kích hoạt…' : stateVI[state]}
              </strong>
            </span>
            {lastRun && !running && (
              <span style={{ fontFamily:'var(--ff-mono)', fontSize:'10.5px', opacity:.6 }}>
                {lastRun}
              </span>
            )}
            <button
              style={{
                marginLeft:'4px', padding:'3px 9px', fontSize:'11px',
                background:'rgba(255,255,255,.10)', color:'#C8F0A0',
                border:'1px solid rgba(255,255,255,.15)', borderRadius:'5px',
                cursor:'pointer', fontFamily:'var(--ff-body)', fontWeight:700,
                display:'flex', alignItems:'center', gap:'4px',
                transition:'background .15s',
              }}
              onClick={handleRun}
              disabled={running}
              onMouseOver={e => e.currentTarget.style.background='rgba(255,255,255,.18)'}
              onMouseOut={e => e.currentTarget.style.background='rgba(255,255,255,.10)'}
            >
              <i className="ti ti-player-play ti-sm"/> Run
            </button>
          </div>
        </div>
      </header>
    );
  }

  MS.Header = Header;
  MS.Toast  = Toast;
}());
