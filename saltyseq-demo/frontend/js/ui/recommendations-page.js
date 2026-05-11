/* ── RecommendationsPage ── */
(function () {
  const { useState } = React;

  const LEVEL_CONFIG = {
    danger: {
      label: 'Nguy hiểm',
      icon: 'ti-alert-triangle',
      color: 'var(--danger-5)',
      bg: 'var(--danger-bg)',
      border: 'var(--danger-bd)',
    },
    medium: {
      label: 'Vừa',
      icon: 'ti-alert-circle',
      color: 'var(--warn-5)',
      bg: 'var(--warn-bg)',
      border: 'var(--warn-bd)',
    },
    safe: {
      label: 'An toàn',
      icon: 'ti-circle-check',
      color: 'var(--safe-5)',
      bg: 'var(--safe-bg)',
      border: 'var(--safe-bd)',
    },
  };

  function getLevel(rate) {
    if (rate >= 0.15) return 'danger';
    if (rate >= 0.05) return 'medium';
    return 'safe';
  }

  function getActions(level, rate30d, rateTotal) {
    if (level === 'danger') {
      return [
        'Ngừng tưới nước kênh — kiểm tra độ mặn trước khi lấy nước',
        'Ưu tiên dùng nước dự trữ hoặc nước mưa trong 48–72h tới',
        rateTotal > rate30d
          ? 'Stress kéo dài nhiều ngày — cần can thiệp sớm, không chờ thêm'
          : 'Stress mới tăng gần đây — theo dõi sát trong 3 ngày tới',
        'Đóng cống ngăn mặn nếu có, hạn chế dẫn nước từ sông',
      ];
    }
    if (level === 'medium') {
      return [
        'Đo độ mặn 2 lần/tuần — đặc biệt buổi sáng sớm',
        'Chuẩn bị nguồn nước ngọt dự phòng (ao, bể chứa)',
        rateTotal > rate30d
          ? 'Xu hướng stress tổng cao hơn gần đây — chú ý theo dõi'
          : 'Tình hình đang cải thiện — duy trì chăm sóc bình thường',
      ];
    }
    return [
      'Tiếp tục canh tác bình thường',
      'Kiểm tra định kỳ hàng tuần là đủ',
    ];
  }

  function StationCard({ station }) {
    const rate30d   = station.stress_rate_30d   ?? 0;
    const rateTotal = station.stress_rate_total ?? 0;
    const level = getLevel(rate30d);
    const cfg   = LEVEL_CONFIG[level];
    const actions = getActions(level, rate30d, rateTotal);

    return (
      <div style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--r-lg)',
        padding: '16px 18px',
        boxShadow: 'var(--sh-sm)',
        transition: 'all .2s ease',
      }}
      onMouseEnter={e => { e.currentTarget.style.boxShadow = 'var(--sh-md)'; }}
      onMouseLeave={e => { e.currentTarget.style.boxShadow = 'var(--sh-sm)'; }}
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <i className="ti ti-map-pin" style={{ fontSize: '16px', color: 'var(--ink-4)' }}/>
            <span style={{ fontFamily: 'var(--ff-heading)', fontSize: '16px', fontWeight: 700, color: 'var(--ink-1)' }}>
              {station.name}
            </span>
            <span style={{ fontFamily: 'var(--ff-body)', fontSize: '11px', color: 'var(--ink-4)' }}>
              · {station.distance_to_estuary_km} km cửa biển
            </span>
          </div>
          <span style={{
            display: 'flex', alignItems: 'center', gap: '4px',
            fontSize: '12px', fontWeight: 700,
            padding: '3px 10px', borderRadius: 'var(--r-sm)',
            background: cfg.bg, color: cfg.color, border: `1px solid ${cfg.border}`,
          }}>
            <i className={`ti ${cfg.icon}`} style={{ fontSize: '12px' }}/>
            {cfg.label}
          </span>
        </div>

        {/* Quick stats */}
        <div style={{
          display: 'flex', marginBottom: '14px',
          background: 'var(--surface-2)', borderRadius: 'var(--r-sm)',
          border: '1px solid var(--border)', overflow: 'hidden',
        }}>
          {[
            ['Stress 30 ngày', `${(rate30d * 100).toFixed(1)}%`,   cfg.color],
            ['Stress tổng',    `${(rateTotal * 100).toFixed(1)}%`, 'var(--ink-2)'],
            ['Cửa biển',       `${station.distance_to_estuary_km} km`, 'var(--teal-5)'],
          ].map(([lbl, val, clr], i, arr) => (
            <div key={lbl} style={{
              flex: 1, padding: '9px 12px', textAlign: 'center',
              borderRight: i < arr.length - 1 ? '1px solid var(--border)' : 'none',
            }}>
              <div style={{ fontSize: '10px', color: 'var(--ink-4)', fontFamily: 'var(--ff-body)', marginBottom: '3px' }}>{lbl}</div>
              <div style={{ fontSize: '14px', fontWeight: 700, fontFamily: 'var(--ff-mono)', color: clr }}>{val}</div>
            </div>
          ))}
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {actions.map((action, i) => (
            <div key={i} style={{
              display: 'flex', alignItems: 'flex-start', gap: '8px',
              fontSize: '13px', color: 'var(--ink-2)', fontFamily: 'var(--ff-body)',
              lineHeight: 1.5,
            }}>
              <i className="ti ti-arrow-right" style={{ fontSize: '13px', color: 'var(--ink-4)', marginTop: '2px', flexShrink: 0 }}/>
              {action}
            </div>
          ))}
        </div>
      </div>
    );
  }

  function RecommendationsPage({ stations }) {
    const [filter, setFilter] = useState('all');

    const enriched = stations.map(s => ({
      ...s,
      _level: getLevel(s.stress_rate_30d ?? 0),
    }));

    const filtered = filter === 'all'
      ? enriched
      : enriched.filter(s => s._level === filter);

    const counts = {
      danger: enriched.filter(s => s._level === 'danger').length,
      medium: enriched.filter(s => s._level === 'medium').length,
      safe:   enriched.filter(s => s._level === 'safe').length,
    };

    const FILTERS = [
      { key: 'all',    label: 'Tất cả',    color: 'var(--ink-2)'    },
      { key: 'danger', label: 'Nguy hiểm', color: 'var(--danger-5)' },
      { key: 'medium', label: 'Vừa',       color: 'var(--warn-5)'   },
      { key: 'safe',   label: 'An toàn',   color: 'var(--safe-5)'   },
    ];

    return (
      <div style={{ display: 'flex', height: 'calc(100vh - 56px)', overflow: 'hidden' }}>

        {/* Sidebar */}
        <div style={{
          width: '240px', flexShrink: 0,
          background: 'var(--surface-2)', borderRight: '1px solid var(--border)',
          padding: '16px 14px', overflowY: 'auto',
        }}>
          <div className="sec-title">
            <i className="ti ti-clipboard-list ti-md" style={{ color: 'var(--teal-5)' }}/>
            Khuyến nghị
          </div>

          <div style={{ marginBottom: '16px', fontFamily: 'var(--ff-body)', fontSize: '12px', color: 'var(--ink-4)', lineHeight: 1.6 }}>
            Gợi ý hành động dựa trên kết quả dự báo mới nhất.
          </div>

          {/* Summary counts */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginBottom: '18px' }}>
            {[
              { key: 'danger', icon: 'ti-alert-triangle', color: 'var(--danger-5)', label: 'Nguy hiểm' },
              { key: 'medium', icon: 'ti-alert-circle',   color: 'var(--warn-5)',   label: 'Vừa'       },
              { key: 'safe',   icon: 'ti-circle-check',   color: 'var(--safe-5)',   label: 'An toàn'   },
            ].map(({ key, icon, color, label }) => (
              <div key={key} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px' }}>
                <i className={`ti ${icon}`} style={{ fontSize: '14px', color }}/>
                <span style={{ fontFamily: 'var(--ff-body)', color: 'var(--ink-3)', flex: 1 }}>{label}</span>
                <span style={{ fontFamily: 'var(--ff-mono)', fontWeight: 700, color }}>{counts[key]}</span>
              </div>
            ))}
          </div>

          {/* Filter buttons */}
          <div style={{ fontFamily: 'var(--ff-body)', fontSize: '11px', color: 'var(--ink-4)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '.06em' }}>
            Lọc theo mức độ
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {FILTERS.map(f => (
              <button
                key={f.key}
                onClick={() => setFilter(f.key)}
                style={{
                  display: 'flex', alignItems: 'center', gap: '8px',
                  padding: '7px 10px', borderRadius: 'var(--r-sm)',
                  border: '1px solid',
                  borderColor: filter === f.key ? f.color : 'transparent',
                  background: filter === f.key ? `color-mix(in srgb, ${f.color} 10%, var(--surface))` : 'transparent',
                  color: filter === f.key ? f.color : 'var(--ink-3)',
                  fontFamily: 'var(--ff-body)', fontSize: '13px',
                  fontWeight: filter === f.key ? 700 : 400,
                  cursor: 'pointer', textAlign: 'left', transition: 'all .15s',
                }}
              >
                {f.label}
                {f.key !== 'all' && (
                  <span style={{ marginLeft: 'auto', fontSize: '11px', fontFamily: 'var(--ff-mono)', fontWeight: 700 }}>
                    {counts[f.key]}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Main content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px' }}>
          {filtered.length === 0 ? (
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              height: '200px', color: 'var(--ink-4)', fontFamily: 'var(--ff-body)', fontSize: '14px',
            }}>
              Không có trạm nào trong mức này.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {filtered.map(s => (
                <StationCard key={s.station_id} station={s} />
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  MS.RecommendationsPage = RecommendationsPage;
}());
