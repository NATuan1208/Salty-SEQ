/* -- RecommendationsPage -- */
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
    if (rate >= 0.50) return 'danger';
    if (rate >= 0.30) return 'medium';
    return 'safe';
  }

  function getActions(level, rate30d, rateTotal) {
    if (level === 'danger') {
      return [
        'Ngừng tưới nước kênh - kiểm tra độ mặn trước khi lấy nước',
        'Ưu tiên dùng nước dự trữ hoặc nước mưa trong 48-72h tới',
        rateTotal > rate30d
          ? 'Stress kéo dài nhiều ngày - cần can thiệp sớm, không chờ thêm'
          : 'Stress mới tăng gần đây - theo dõi sát trong 3 ngày tới',
        'Đóng cống ngăn mặn nếu có, hạn chế dẫn nước từ sông',
      ];
    }

    if (level === 'medium') {
      return [
        'Đo độ mặn 2 lần/tuần - đặc biệt buổi sáng sớm',
        'Chuẩn bị nguồn nước ngọt dự phòng (ao, bể chứa)',
        rateTotal > rate30d
          ? 'Xu hướng stress tổng cao hơn gần đây - chú ý theo dõi'
          : 'Tình hình đang cải thiện - duy trì chăm sóc bình thường',
      ];
    }

    return [
      'Tiếp tục canh tác bình thường',
      'Kiểm tra định kỳ hằng tuần là đủ',
    ];
  }

  function StationCard({ station }) {
    const rate30d = station.stress_rate_30d ?? 0;
    const rateTotal = station.stress_rate_total ?? 0;
    const level = station._level;
    const cfg = LEVEL_CONFIG[level];
    const actions = station._api_actions || getActions(level, rate30d, rateTotal);

    return (
      <div
        style={{
          background: level === 'danger'
            ? 'color-mix(in srgb, var(--danger-lt) 34%, var(--surface))'
            : level === 'medium'
              ? 'color-mix(in srgb, var(--warn-lt) 22%, var(--surface))'
              : 'var(--surface)',
          border: 'none',
          borderLeft: 'none',
          borderRadius: 'var(--r-lg)',
          padding: '16px 18px',
          boxShadow: level === 'danger' ? 'var(--sh-sm)' : 'var(--sh-xs)',
          transition: 'all .2s ease',
        }}
        onMouseEnter={e => { e.currentTarget.style.boxShadow = 'var(--sh-sm)'; }}
        onMouseLeave={e => { e.currentTarget.style.boxShadow = level === 'danger' ? 'var(--sh-sm)' : 'var(--sh-xs)'; }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', marginBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
            <i className="ti ti-map-pin" style={{ fontSize: '16px', color: 'var(--ink-4)' }} />
            <span style={{ fontFamily: 'var(--ff-heading)', fontSize: '16px', fontWeight: 700, color: 'var(--ink-1)' }}>
              {station.name}
            </span>
            <span style={{ fontFamily: 'var(--ff-body)', fontSize: '11px', color: 'var(--ink-4)' }}>
              · {station.distance_to_estuary_km} km cửa biển
            </span>
          </div>

          <span
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '12px',
              fontWeight: 700,
              padding: '3px 10px',
              borderRadius: 'var(--r-sm)',
              background: cfg.bg,
              color: cfg.color,
              border: `1px solid ${cfg.border}`,
              flexShrink: 0,
            }}
          >
            <i className={`ti ${cfg.icon}`} style={{ fontSize: '12px' }} />
            {cfg.label}
          </span>
        </div>

        <div
          style={{
            display: 'flex',
            marginBottom: '14px',
            background: 'var(--surface-2)',
            borderRadius: 'var(--r-sm)',
            border: '1px solid var(--border)',
            overflow: 'hidden',
          }}
        >
          {[
            ['Stress 30 ngày', `${(rate30d * 100).toFixed(1)}%`, cfg.color],
            ['Stress tổng', `${(rateTotal * 100).toFixed(1)}%`, 'var(--ink-2)'],
            ['Cửa biển', `${station.distance_to_estuary_km} km`, 'var(--teal-5)'],
          ].map(([label, value, color], index, arr) => (
            <div
              key={label}
              style={{
                flex: 1,
                padding: '9px 12px',
                textAlign: 'center',
                borderRight: index < arr.length - 1 ? '1px solid var(--border)' : 'none',
              }}
            >
              <div style={{ fontSize: '10px', color: 'var(--ink-4)', fontFamily: 'var(--ff-body)', marginBottom: '3px' }}>
                {label}
              </div>
              <div style={{ fontSize: '14px', fontWeight: 700, fontFamily: 'var(--ff-mono)', color }}>
                {value}
              </div>
            </div>
          ))}
        </div>

        {station._is_current && (
          <div
            style={{
              fontSize: '11px',
              color: 'var(--teal-5)',
              background: 'color-mix(in srgb, var(--teal-5) 10%, var(--surface))',
              padding: '4px 8px',
              borderRadius: 'var(--r-sm)',
              marginBottom: '10px',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              border: '1px solid var(--border)',
            }}
          >
            <i className="ti ti-activity" style={{ fontSize: '12px' }} />
            Khuyến nghị theo ngữ cảnh phân tích hiện tại
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {actions.map((action, index) => (
            <div
              key={index}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '8px',
                fontSize: '13px',
                color: 'var(--ink-2)',
                fontFamily: 'var(--ff-body)',
                lineHeight: 1.5,
              }}
            >
              <i className="ti ti-arrow-right" style={{ fontSize: '13px', color: 'var(--ink-4)', marginTop: '2px', flexShrink: 0 }} />
              {action}
            </div>
          ))}
        </div>
      </div>
    );
  }

  function RecommendationsPage({ stations, currentResult, selectedStation }) {
    const [filter, setFilter] = useState('all');
    const [stationFilter, setStationFilter] = useState('all');
    const [maxDistance, setMaxDistance] = useState(50);
    const [minStress30d, setMinStress30d] = useState(0);
    const [actionOnly, setActionOnly] = useState(false);

    const enriched = stations.map(station => {
      let level = getLevel(station.stress_rate_30d ?? 0);
      let apiActions = null;
      let isCurrent = false;

      if (currentResult && station.station_id === selectedStation) {
        const label = (currentResult.label || '').toLowerCase();
        if (label === 'danger') level = 'danger';
        else if (label === 'warning') level = 'medium';
        else level = 'safe';

        if (currentResult.recommendations) {
          apiActions = currentResult.recommendations;
        }
        isCurrent = true;
      }

      return {
        ...station,
        _level: level,
        _api_actions: apiActions,
        _is_current: isCurrent,
        _needs_action: level !== 'safe',
      };
    });

    const severityOrder = { danger: 0, medium: 1, safe: 2 };

    const filtered = enriched.filter(station => {
      if (filter !== 'all' && station._level !== filter) return false;
      if (stationFilter !== 'all' && station.station_id !== stationFilter) return false;
      if ((station.distance_to_estuary_km ?? 999) > maxDistance) return false;
      if (((station.stress_rate_30d ?? 0) * 100) < minStress30d) return false;
      if (actionOnly && !station._needs_action) return false;
      return true;
    }).sort((a, b) =>
      severityOrder[a._level] - severityOrder[b._level] ||
      (b.stress_rate_30d ?? 0) - (a.stress_rate_30d ?? 0)
    );

    const counts = {
      danger: enriched.filter(station => station._level === 'danger').length,
      medium: enriched.filter(station => station._level === 'medium').length,
      safe: enriched.filter(station => station._level === 'safe').length,
    };

    const filters = [
      { key: 'all', label: 'Tất cả', color: 'var(--ink-2)' },
      { key: 'danger', label: 'Nguy hiểm', color: 'var(--danger-5)' },
      { key: 'medium', label: 'Vừa', color: 'var(--warn-5)' },
      { key: 'safe', label: 'An toàn', color: 'var(--safe-5)' },
    ];

    const resetFilters = () => {
      setFilter('all');
      setStationFilter('all');
      setMaxDistance(50);
      setMinStress30d(0);
      setActionOnly(false);
    };

    return (
      <div style={{ display: 'flex', height: 'calc(100vh - 50px)', overflow: 'hidden' }}>
        <div
          style={{
            width: '240px',
            flexShrink: 0,
            background: 'var(--surface-2)',
            borderRight: '1px solid var(--border)',
            padding: '16px 14px',
            overflowY: 'auto',
          }}
        >
          <div className="sec-title">
            <i className="ti ti-clipboard-list ti-md" style={{ color: 'var(--teal-5)' }} />
            Khuyến nghị
          </div>

          <div style={{ marginBottom: '14px', fontFamily: 'var(--ff-body)', fontSize: '12px', color: 'var(--ink-4)', lineHeight: 1.6 }}>
            Gợi ý hành động dựa trên kết quả dự báo mới nhất.
          </div>

          <div style={{ fontFamily: 'var(--ff-body)', fontSize: '11px', color: 'var(--ink-4)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '.06em' }}>
            Lọc theo mức độ
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {filters.map(item => (
              <button
                key={item.key}
                onClick={() => setFilter(item.key)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '8px 10px',
                  borderRadius: 'var(--r-sm)',
                  border: '1px solid',
                  borderColor: filter === item.key ? item.color : 'transparent',
                  background: filter === item.key ? `color-mix(in srgb, ${item.color} 10%, var(--surface))` : 'transparent',
                  color: filter === item.key ? item.color : 'var(--ink-3)',
                  fontFamily: 'var(--ff-body)',
                  fontSize: '13px',
                  fontWeight: filter === item.key ? 700 : 400,
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'all .15s',
                }}
              >
                {item.label}
                {item.key !== 'all' && (
                  <span style={{ marginLeft: 'auto', fontSize: '11px', fontFamily: 'var(--ff-mono)', fontWeight: 700 }}>
                    {counts[item.key]}
                  </span>
                )}
              </button>
            ))}
          </div>

          <div style={{ marginTop: '16px', fontFamily: 'var(--ff-body)', fontSize: '11px', color: 'var(--ink-4)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '.06em' }}>
            Lọc nâng cao
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <label style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
              <span style={{ fontSize: '11px', color: 'var(--ink-4)', fontWeight: 700 }}>Trạm</span>
              <select
                className="fctl"
                value={stationFilter}
                onChange={event => setStationFilter(event.target.value)}
                style={{ fontSize: '12px', padding: '7px 10px' }}
              >
                <option value="all">Tất cả trạm</option>
                {enriched.map(station => (
                  <option key={station.station_id} value={station.station_id}>{station.name}</option>
                ))}
              </select>
            </label>

            <label style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
              <span style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--ink-4)', fontWeight: 700 }}>
                <span>Cửa biển tối đa</span>
                <span style={{ fontFamily: 'var(--ff-mono)', color: 'var(--teal-5)' }}>{maxDistance} km</span>
              </span>
              <input
                type="range"
                min="0"
                max="50"
                step="1"
                value={maxDistance}
                onChange={event => setMaxDistance(Number(event.target.value))}
              />
            </label>

            <label style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
              <span style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--ink-4)', fontWeight: 700 }}>
                <span>Stress 30 ngày từ</span>
                <span style={{ fontFamily: 'var(--ff-mono)', color: 'var(--warn-5)' }}>{minStress30d}%</span>
              </span>
              <input
                type="range"
                min="0"
                max="100"
                step="1"
                value={minStress30d}
                onChange={event => setMinStress30d(Number(event.target.value))}
              />
            </label>

            <label
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 10px',
                borderRadius: 'var(--r-sm)',
                background: actionOnly ? 'var(--warn-lt)' : 'transparent',
                border: `1px solid ${actionOnly ? 'var(--warn-bd)' : 'var(--border)'}`,
                color: actionOnly ? 'var(--warn-5)' : 'var(--ink-3)',
                cursor: 'pointer',
                fontSize: '12px',
                fontWeight: 700,
              }}
            >
              <input
                type="checkbox"
                checked={actionOnly}
                onChange={event => setActionOnly(event.target.checked)}
              />
              Chỉ trạm cần hành động
            </label>

            <button className="btn-sm" onClick={resetFilters} style={{ justifyContent: 'center' }}>
              <i className="ti ti-rotate-clockwise" style={{ fontSize: '13px' }} />
              Xóa lọc
            </button>

            <div
              style={{
                fontFamily: 'var(--ff-mono)',
                fontSize: '10px',
                color: 'var(--ink-4)',
                paddingTop: '2px',
                display: 'flex',
                justifyContent: 'space-between',
              }}
            >
              <span>Đang hiển thị</span>
              <b style={{ color: 'var(--ink-2)' }}>{filtered.length}/{enriched.length}</b>
            </div>
          </div>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px' }}>
          {filtered.length === 0 ? (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '200px',
                color: 'var(--ink-4)',
                fontFamily: 'var(--ff-body)',
                fontSize: '14px',
              }}
            >
              Không có trạm nào khớp bộ lọc.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {filtered.map(station => (
                <StationCard key={station.station_id} station={station} />
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  MS.RecommendationsPage = RecommendationsPage;
}());
