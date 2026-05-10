/* ── StationMap + StationList + MapPanel ── */
(function () {
  const { useEffect, useRef } = React;

  function StationMap({ stations, selected, onSelect }) {
    const divRef = useRef(null);
    const mapRef = useRef(null);
    const mkRef  = useRef({});

    useEffect(() => {
      if (!divRef.current || mapRef.current) return;
      const map = L.map(divRef.current, {
        center: [10.12, 106.55],
        zoom: 10,
        zoomControl: true,
        attributionControl: false,
      });

      

      /* CartoDB Voyager — warm, natural colours, great for agriculture */
      L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
        subdomains: 'abcd',
        maxZoom: 19,
      }).addTo(map);

      L.control.attribution({ prefix: false })
        .addAttribution('© <a href="https://www.openstreetmap.org/copyright">OSM</a> © <a href="https://carto.com">CARTO</a>')
        .addTo(map);

      mapRef.current = map;
      return () => {
        if (mapRef.current) { mapRef.current.remove(); mapRef.current = null; }
      };
    }, []);

    useEffect(() => {
      const map = mapRef.current;
      if (!map || !selected) return;

      // Tìm dữ liệu của trạm đang được chọn
      const s = stations.find(st => st.station_id === selected);
      
      if (s) {
        // map.flyTo([vĩ độ, kinh độ], mức độ zoom, { tùy chọn })
        map.flyTo([s.lat, s.lon], 11, {
          animate: true,
          duration: 1.5 // thời gian bay là 1.5 giây cho mượt
        });
      }
    }, [selected, stations]);

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
          radius:      isSel ? 15 : 12,
          fillColor:   col,
          color:       isSel ? '#1B3A0E' : 'white',
          weight:      isSel ? 3 : 1.5,
          fillOpacity: isSel ? .95 : .82,
        }).addTo(map);

        mk.bindTooltip(
          `<div style="line-height:1.5">
             <b style="font-size:13px">${s.name}</b><br>
             Stress 30d: <b style="color:${col}">${(rate * 100).toFixed(1)}%</b><br>
             <span style="color:#587A40;font-size:11px">
               <i class="ti ti-map-pin" style="font-size:10px"></i>
               ${s.distance_to_estuary_km} km tới cửa biển
             </span>
           </div>`,
          { sticky: true }
        );

        mk.on('click', () => onSelect(s.station_id));
        mk.on('mouseover', function() {
          if (s.station_id !== selected)
            this.setStyle({ radius: 14, fillOpacity: .92 });
        });
        mk.on('mouseout', function() {
          if (s.station_id !== selected)
            this.setStyle({ radius: 12, fillOpacity: .82 });
        });

        mkRef.current[s.station_id] = mk;
      });
    }, [stations, selected]);

    return <div ref={divRef} className="map-wrap"/>;
  }

  function StationList({ stations, selected, onSelect }) {
    return (
      <div>
        {stations.map(s => {
          const rate  = s.stress_rate_30d ?? 0.1;
          const col   = rate >= 0.15 ? '#C82020' : rate >= 0.05 ? '#C48020' : '#0FA860';
          const isSel = s.station_id === selected;
          return (
            <div
              key={s.station_id}
              className={`stn-card${isSel ? ' sel' : ''}`}
              style={{ '--stn-clr': col }}
              onClick={() => onSelect(s.station_id)}
            >
              <div className="stn-dot" style={{ background: col }}/>
              <div className="stn-info">
                <div className="stn-name">
                  <i className="ti ti-building-broadcast-tower" style={{ fontSize:'11px', marginRight:'4px', opacity:.6 }}/>
                  {s.name}
                </div>
                <div className="stn-meta">
                  {s.distance_to_estuary_km} km · cửa biển
                </div>
              </div>
              <span
                className="stn-rate"
                style={{
                  background: `color-mix(in srgb, ${col} 12%, white)`,
                  color: col,
                  border: `1px solid color-mix(in srgb, ${col} 30%, white)`,
                }}
              >
                {(rate * 100).toFixed(0)}%
              </span>
            </div>
          );
        })}
      </div>
    );
  }

  function MapPanel({ stations, selected, onSelect }) {
    return (
      <div className="panel panel-left">
        <div className="sec-title">
          <i className="ti ti-map-2 ti-md" style={{ color:'var(--teal-5)' }}/>
          Bản đồ quan trắc
          <span className="sec-title-badge">{stations.length} trạm</span>
        </div>

        {stations.length > 0
          ? <StationMap stations={stations} selected={selected} onSelect={onSelect}/>
          : (
            <div className="map-wrap" style={{ display:'flex', alignItems:'center', justifyContent:'center', background:'var(--surface-3)' }}>
              <div style={{ textAlign:'center', color:'var(--ink-4)' }}>
                <span className="spinner dark" style={{ display:'block', margin:'0 auto 8px' }}/>
                <div style={{ fontSize:'12px' }}>Đang kết nối server…</div>
              </div>
            </div>
          )
        }

        {/* Legend */}
        <div style={{
          display:'flex', gap:'12px', justifyContent:'center',
          margin:'6px 0 10px', flexWrap:'wrap',
        }}>
          {[['#0FA860','Thấp (<5%)'],['#C48020','Vừa (5–15%)'],['#C82020','Cao (>15%)']].map(([c,l]) => (
            <div key={l} style={{ display:'flex', alignItems:'center', gap:'5px', fontFamily:'var(--ff-body)', fontSize:'11px', color:'var(--ink-3)' }}>
              <div style={{ width:'9px', height:'9px', borderRadius:'50%', background:c, flexShrink:0 }}/>
              {l}
            </div>
          ))}
        </div>

        <StationList stations={stations} selected={selected} onSelect={onSelect}/>
      </div>
    );
  }

  MS.MapPanel = MapPanel;
}());
