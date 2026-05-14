/* ── Global namespace ── */
const MS = window.MS = {};

MS.API = 'http://localhost:8000/api';

MS.STATIONS = {
  BT_BaTri:     { name:'Ba Tri',      lat:10.0355, lon:106.6041, dist:22.5 },
  BT_BinhDai:   { name:'Bình Đại',    lat:10.1499, lon:106.7905, dist:8.3  },
  BT_ChauThanh: { name:'Châu Thành',  lat:10.2499, lon:106.4314, dist:38.1 },
  BT_GiongTrom: { name:'Giồng Trôm',  lat:10.1009, lon:106.4736, dist:29.6 },
  BT_ThanhPhu:  { name:'Thạnh Phú',   lat:9.9049,  lon:106.5921, dist:5.2  },
};

MS.FEATURE_GROUPS = {
  veg: {
    icon: 'ti-leaf',
    label: 'Thực vật',
    fields: [
      { key:'ndvi',           label:'NDVI',            step:.001  },
      { key:'ndvi_tendency',  label:'NDVI tendency',   step:.0001 },
      { key:'ndvi_lag_1',     label:'NDVI lag-1d',     step:.001  },
      { key:'ndvi_7d_avg',    label:'NDVI 7d avg',     step:.001  },
      { key:'lst',            label:'LST (°C)',         step:.1    },
      { key:'lst_ndvi_ratio', label:'LST/NDVI ratio',  step:.1    },
    ],
  },
  sal: {
    icon: 'ti-droplet',
    label: 'Độ mặn',
    fields: [
      { key:'salinity_psu',       label:'Salinity (PSU)',   step:.01  },
      { key:'salinity_7d_avg',    label:'7d avg (PSU)',     step:.01  },
      { key:'salinity_7d_median', label:'7d median',        step:.01  },
      { key:'salinity_tendency',  label:'Tendency',         step:.001 },
    ],
  },
  climate: {
    icon: 'ti-cloud-rain',
    label: 'Khí hậu',
    fields: [
      { key:'temp_mean',     label:'Nhiệt độ TB (°C)', step:.1 },
      { key:'temp_max',      label:'Nhiệt độ max',     step:.1 },
      { key:'precipitation', label:'Mưa (mm)',          step:.1 },
      { key:'precip_7d_sum', label:'Mưa 7d (mm)',       step:.1 },
      { key:'et0',           label:'ET0 (mm)',           step:.01 },
    ],
  },
  soil: {
    icon: 'ti-plant',
    label: 'Đất & Khác',
    fields: [
      { key:'soil_moisture_surface',      label:'SM surface (m³/m³)', step:.001 },
      { key:'soil_temp',                  label:'Nhiệt đất (°C)',     step:.1   },
      { key:'heatwave_consecutive_days',  label:'Nắng nóng (ngày)',   step:1    },
      { key:'days_without_rain',          label:'Không mưa (ngày)',   step:1    },
    ],
  },
};

MS.STATE_LABELS = {
  Salt_High:'Mặn cao', Salt_Mid:'Mặn vừa', Salt_Low:'Mặn thấp',
  Soil_Dry:'Đất khô',  Soil_Wet:'Đất ướt',
  Temp_Cool:'Nhiệt mát', Temp_Mild:'Nhiệt vừa', Temp_Hot:'Nhiệt cao',
  Rain_None:'Không mưa', Rain_Light:'Mưa nhẹ', Rain_Heavy:'Mưa lớn',
  Plant_DANGER:'Nguy hiểm', Plant_Warning:'Cảnh báo', Plant_Safe:'An toàn',
};

MS.FEATURE_COLORS = {
  ndvi:'#0D9488', ndvi_tendency:'#0D9488', ndvi_lag_1:'#0D9488', ndvi_lag_7:'#0D9488', ndvi_7d_avg:'#0D9488',
  salinity_psu:'#D97706', salinity_7d_median:'#D97706', salinity_7d_avg:'#D97706',
  lst_ndvi_ratio:'#EA580C', lst:'#EA580C',
  lat:'#7C3AED', lon:'#7C3AED', distance_to_estuary_km:'#8B5CF6',
  day_of_year:'#6366F1', month:'#6366F1',
};

/* ── API helpers ── */
MS.api = {
  get: async (path) => {
    const r = await fetch(`${MS.API}${path}`);
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    return r.json();
  },
  post: async (path, body) => {
    const r = await fetch(`${MS.API}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    return r.json();
  },
  del: async (path) => {
    const r = await fetch(`${MS.API}${path}`, { method: 'DELETE' });
    if (!r.ok) throw new Error(`${r.status}`);
    return r.json();
  },
};

/* ── Design helpers ── */
MS.stressColor = function(rate) {
  if (rate > 0.50) return '#EF4444';
  if (rate > 0.30) return '#F59E0B';
  return '#10B981';
};

MS.stressVar = function(rate) {
  if (rate > 0.50) return 'var(--danger-5)';
  if (rate > 0.30) return 'var(--warn-5)';
  return 'var(--safe-5)';
};

MS.chipStyle = function(state) {
  const map = {
    Plant_DANGER:   { bg:'var(--danger-lt)',  bd:'var(--danger-bd)', tx:'var(--danger-5)' },
    Plant_Warning:  { bg:'var(--warn-lt)',    bd:'var(--warn-bd)',   tx:'var(--warn-5)'   },
    Plant_Safe:     { bg:'var(--safe-lt)',    bd:'var(--safe-bd)',   tx:'var(--safe-5)'   },
    Salt_High:      { bg:'#FFF7ED',           bd:'#FDBA74',          tx:'#EA580C'         },
    Salt_Mid:       { bg:'var(--warn-lt)',    bd:'var(--warn-bd)',   tx:'var(--warn)'     },
    Salt_Low:       { bg:'var(--safe-lt)',    bd:'var(--safe-bd)',   tx:'var(--safe)'     },
    Soil_Dry:       { bg:'#FFF7ED',           bd:'#FDBA74',          tx:'#B45309'         },
    Soil_Wet:       { bg:'var(--teal-lt)',    bd:'var(--teal-bd)',   tx:'var(--teal)'     },
    Temp_Cool:      { bg:'#EFF6FF',           bd:'#BFDBFE',          tx:'#1D4ED8'         },
    Temp_Mild:      { bg:'#ECFDF3',           bd:'#BBF7D0',          tx:'#16A34A'         },
    Temp_Hot:       { bg:'#FFF7ED',           bd:'#FDBA74',          tx:'#EA580C'         },
    Rain_None:      { bg:'#F8FAFC',           bd:'#CBD5F5',          tx:'#64748B'         },
    Rain_Light:     { bg:'#E0F2FE',           bd:'#7DD3FC',          tx:'#0284C7'         },
    Rain_Heavy:     { bg:'#DBEAFE',           bd:'#93C5FD',          tx:'#1D4ED8'         },
  };
  for (const [k,v] of Object.entries(map)) {
    if (state.includes(k)) return v;
  }
  return { bg:'var(--surface-3)', bd:'var(--border-md)', tx:'var(--ink-3)' };
};
