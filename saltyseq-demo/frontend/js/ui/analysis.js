/* ── SpmPatterns + FeatureBars + HistoryTable + RightPanel ── */
(function () {
  const { useState, useCallback } = React;

  /* ── State chip ── */
  function StateChip({ state }) {
    const s = MS.chipStyle(state);
    const label = MS.STATE_LABELS[state] || state;
    return (
      <span className="state-chip" style={{ background:s.bg, borderColor:s.bd, color:s.tx }}>
        {label}
      </span>
    );
  }

  function CompactState({ str }) {
    return (
      <span style={{ display:'inline-flex', gap:'3px', flexWrap:'wrap' }}>
        {str.split('|').map((p, i) => <StateChip key={i} state={p} />)}
      </span>
    );
  }

  /* ── Single SPM pattern card ── */
  function PatternCard({ pattern, support, support_pct, type, label_vi }) {
    return (
      <div className={`pat-card ${type}`}>
        <span className={`pat-badge ${type}`}>
          {type === 'danger'
            ? <><i className="ti ti-alert-triangle ti-sm" /> DANGER</>
            : <><i className="ti ti-alert-circle ti-sm" /> WARNING</>}
        </span>

        <div className="pat-chips">
          {pattern.map((s, i) => (
            <React.Fragment key={i}>
              {i > 0 && <span className="pat-arrow">→</span>}
              <CompactState str={s} />
            </React.Fragment>
          ))}
        </div>

        <div className="pat-support">
          <i className="ti ti-chart-bar ti-sm" style={{ marginRight:'4px', color:'var(--ink-4)' }} />
          <b>{support}</b> lần &nbsp;·&nbsp;
          {typeof support_pct === 'number' ? support_pct.toFixed(1) : support_pct}% sequences
        </div>

        {label_vi && <div className="pat-label-vi">{label_vi}</div>}
      </div>
    );
  }

  function PatternGroup({ title, type, patterns, defaultOpen }) {
    const [open, setOpen] = useState(defaultOpen);
    if (!patterns.length) return null;

    const cfg = type === 'danger'
      ? { icon: 'ti-alert-triangle', color: 'var(--danger-5)', bg: 'var(--danger-lt)', bd: 'var(--danger-bd)' }
      : { icon: 'ti-alert-circle', color: 'var(--warn-5)', bg: 'var(--warn-lt)', bd: 'var(--warn-bd)' };

    return (
      <div className={`spm-group ${type}`}>
        <button
          className="spm-group-head"
          onClick={() => setOpen(v => !v)}
          style={{
            color: cfg.color,
            background: `color-mix(in srgb, ${cfg.bg} 42%, var(--surface))`,
            borderColor: cfg.bd,
          }}
        >
          <span>
            <i className={`ti ${cfg.icon} ti-sm`} />
            {title}
          </span>
          <span className="spm-group-count">{patterns.length}</span>
          <i className={`ti ${open ? 'ti-chevron-up' : 'ti-chevron-down'} ti-sm`} />
        </button>

        {open && (
          <div className="spm-group-body">
            {patterns.map((p, i) => <PatternCard key={i} {...p} />)}
          </div>
        )}
      </div>
    );
  }

  /* ── Feature importance bar chart ── */
  function FeatureBars({ features }) {
    if (!features?.length) return (
      <div className="ph" style={{ padding:'14px' }}>
        <span style={{ fontSize:'12px', color:'var(--ink-4)' }}>Chưa có kết quả phân tích</span>
      </div>
    );

    const data = features.slice(0, 8);
    const mx   = Math.max(...data.map(f => f.importance));

    return (
      <div>
        {data.map(f => (
          <div key={f.feature} className="fbar">
            <span className="fbar-name" title={f.feature}>{f.feature.replace(/_/g, ' ')}</span>
            <div className="fbar-track">
              <div
                className="fbar-fill"
                style={{
                  width: `${(f.importance / mx) * 100}%`,
                  background: `linear-gradient(90deg, ${(MS.FEATURE_COLORS[f.feature] || '#0D9488')}99, ${MS.FEATURE_COLORS[f.feature] || '#0D9488'})`,
                }}
              />
            </div>
            <span className="fbar-val">{Math.round(f.importance)}</span>
          </div>
        ))}
        <div style={{ marginTop:'8px', fontSize:'10px', color:'var(--ink-4)', fontFamily:'var(--ff-mono)', textAlign:'right' }}>
          XGBoost gain score
        </div>
      </div>
    );
  }

  /* ── History table ── */
  function HistoryTable({ history, onDelete, onClearAll }) {
    const displayHistory = [];
    const seen = new Set();
    history.forEach(h => {
      const key = `${h.station_id || h.station_name}-${h.date}`;
      if (seen.has(key) || displayHistory.length >= 5) return;
      seen.add(key);
      displayHistory.push(h);
    });

    if (!displayHistory.length) return (
      <div className="ph" style={{ border:'1px dashed var(--border)', borderRadius:'var(--r-md)' }}>
        <i className="ti ti-history ph-icon" />
        <span>Chưa có lịch sử dự báo</span>
      </div>
    );

    return (
      <div>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'8px' }}>
          <span style={{ fontFamily:'var(--ff-mono)', fontSize:'10.5px', color:'var(--ink-4)' }}>
            {displayHistory.length} gần nhất
          </span>
          <button className="btn-sm danger" onClick={onClearAll}>
            <i className="ti ti-trash ti-sm" /> Xóa tất cả
          </button>
        </div>
        <table className="hist-table">
          <thead>
            <tr>
              <th>Ngày</th>
              <th>Trạm</th>
              <th>Score</th>
              <th>Kết quả</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {displayHistory.map(h => (
              <tr key={h.id}>
                <td style={{ fontFamily:'var(--ff-mono)', fontSize:'11px', color:'var(--ink-4)' }}>
                  {h.date}
                </td>
                <td style={{ fontSize:'12.5px', color:'var(--ink-2)', fontWeight:600 }}>
                  {h.station_name}
                </td>
                <td style={{ fontFamily:'var(--ff-mono)', fontSize:'12.5px', fontWeight:700, color:'var(--ink-1)' }}>
                  {(h.probability * 100).toFixed(1)}%
                </td>
                <td>
                  <span className={`label-pill ${h.label}`}>{h.label}</span>
                </td>
                <td>
                  <button className="btn-icon" onClick={() => onDelete(h.id)} title="Xóa">
                    <i className="ti ti-x" style={{ fontSize:'13px' }} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  /* ── Right panel ── */
  function AnalysisPanel({ result, history, onDeleteHistory, onClearHistory }) {
    const matchedPatterns = result?.matched_patterns || [];
    const dangerPatterns = matchedPatterns.filter(p => p.type === 'danger');
    const warningPatterns = matchedPatterns.filter(p => p.type !== 'danger');

    return (
      <div className="panel panel-right">

        {/* SPM Patterns */}
        <div className="sec">
          <div className="sec-title">
            <i className="ti ti-search" style={{ color:'var(--teal-5)' }} />
            Chuỗi cảnh báo SPM
            {result?.matched_patterns?.length > 0 && (
              <span className="sec-title-count">{result.matched_patterns.length} matched</span>
            )}
          </div>

          {matchedPatterns.length > 0
            ? (
              <div className="spm-group-list">
                <PatternGroup
                  title="Nguy hiểm"
                  type="danger"
                  patterns={dangerPatterns}
                  defaultOpen={dangerPatterns.length > 0}
                />
                <PatternGroup
                  title="Cảnh báo"
                  type="warning"
                  patterns={warningPatterns}
                  defaultOpen={dangerPatterns.length === 0}
                />
              </div>
            )
            : (
              <div className="ph" style={{ border:'1px dashed var(--border)', borderRadius:'var(--r-md)', marginBottom:'12px' }}>
                <i className="ti ti-microscope ph-icon" />
                <span>Nhấn <em>PHÂN TÍCH</em> để xem</span>
                <span style={{ fontSize:'11.5px' }}>Subsequence matching 14-day lookback</span>
              </div>
            )
          }
        </div>

        {/* Feature importance */}
        <div className="sec">
          <div className="sec-title">
            <i className="ti ti-chart-bar" style={{ color:'var(--amber-5)' }} />
            Feature Importance
          </div>
          <div className="card">
            <FeatureBars features={result?.feature_top10} />
          </div>
        </div>

        {/* History */}
        <div className="sec">
          <div className="sec-title">
            <i className="ti ti-history" style={{ color:'var(--ink-3)' }} />
            Lịch sử dự báo
          </div>
          <div className="card">
            <HistoryTable
              history={history}
              onDelete={onDeleteHistory}
              onClearAll={onClearHistory}
            />
          </div>
        </div>
      </div>
    );
  }

  MS.AnalysisPanel = AnalysisPanel;
  MS.StateChip = StateChip;
}());
