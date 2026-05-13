/* ── FeaturesPage — Chi tiết đặc trưng (Feature Encyclopedia) ── */
(function () {
  const { useState, useEffect, useRef, useCallback } = React;

  /* ═══════════════════════════════════════════════════════════
     DATA — full feature catalogue
  ═══════════════════════════════════════════════════════════ */
  const FEATURE_GROUPS_DATA = [
    {
      id: 'vegetation',
      icon: 'ti-leaf',
      label: 'Thực vật',
      emoji: '🌿',
      color: '#0D9488',
      colorLight: 'color-mix(in srgb, #0D9488 12%, var(--surface))',
      colorBorder: 'color-mix(in srgb, #0D9488 30%, var(--border))',
      colorGlow: 'rgba(13,148,136,.18)',
      colorGlowStrong: 'rgba(13,148,136,.35)',
      summary: 'Theo dõi sức khỏe và tình trạng phát triển của cây trồng qua ảnh viễn thám vệ tinh (NASA MODIS).',
      features: [
        {
          key: 'ndvi', label: 'NDVI', unit: '[-1 → 1]', icon: 'ti-plant-2',
          importance: 103.0, rank: 2, short: 'Chỉ số thực vật hiện tại',
          desc: 'Normalized Difference Vegetation Index — chỉ số chuẩn hóa phản ánh độ "xanh tốt" và sinh khối của cây. Thang đo từ -1 đến 1: giá trị gần 1 nghĩa là cây trồng rất khỏe, nhiều sinh khối; giá trị âm thường là mặt nước hoặc đất trống.',
          detail: 'NDVI giảm mạnh là tín hiệu sớm cây đang bị sốc (stress) do mặn hoặc hạn. NDVI được tính từ ảnh vệ tinh MODIS 250m, chu kỳ 16 ngày. Trong mô hình này, NDVI là feature xếp hạng #2 theo XGBoost gain score (103.0).',
          danger: 'NDVI < 0.2: cây gần như không quang hợp được, nguy cơ chết cây rất cao.',
          tip: 'Theo dõi NDVI theo chuỗi thời gian quan trọng hơn nhìn giá trị tại một thời điểm.',
        },
        {
          key: 'ndvi_tendency', label: 'NDVI tendency', unit: '[Δ/ngày]', icon: 'ti-trending-down',
          importance: 245.1, rank: 1, short: 'Xu hướng NDVI — Feature quan trọng nhất (#1)',
          desc: 'Tốc độ thay đổi của NDVI ở thời điểm hiện tại so với thời gian trước đó (đạo hàm bậc nhất). Cho biết cây đang trong đà phục hồi (giá trị dương) hay đang héo úa dần (giá trị âm).',
          detail: 'Đây là feature QUAN TRỌNG NHẤT của mô hình (XGBoost gain = 245.1, bỏ xa feature #2). Ngay cả khi salinity thấp, nếu NDVI tendency âm mạnh, mô hình vẫn có thể phát cảnh báo DANGER.',
          danger: 'ndvi_tendency < -0.01/ngày trong nhiều ngày liên tiếp: cây đang sụp NDVI nhanh, cần can thiệp.',
          tip: 'Kịch bản B (2025-06-15): salinity 10 PSU nhưng NDVI tendency âm mạnh → mô hình báo DANGER.',
        },
        {
          key: 'ndvi_lag_1', label: 'NDVI lag-1', unit: '[-1 → 1]', icon: 'ti-history',
          importance: 54.9, rank: 5, short: 'NDVI 1 chu kỳ trước',
          desc: 'Giá trị NDVI của 1 chu kỳ thời gian trước đó. Giúp mô hình AI nhìn được "bệnh án" lịch sử của cây trồng thay vì chỉ nhìn vào hiện tại.',
          detail: 'Lag features cho phép mô hình phát hiện cấu trúc thời gian: nếu NDVI lag-1 cao mà NDVI hiện tại thấp hơn nhiều, có thể cây vừa trải qua cú sốc.',
          danger: 'Sụt giảm lớn giữa ndvi_lag_1 và ndvi hiện tại (Δ > 0.1) là dấu hiệu cú sốc cấp tính.',
          tip: 'Được sử dụng cùng ndvi_lag_3, ndvi_lag_7 để tạo chuỗi lịch sử cho mô hình học.',
        },
        {
          key: 'ndvi_7d_avg', label: 'NDVI 7d avg', unit: '[-1 → 1]', icon: 'ti-chart-line',
          importance: null, rank: null, short: 'NDVI trung bình 7 ngày',
          desc: 'Giá trị trung bình trượt (rolling mean) của NDVI trong 7 ngày. Giúp loại bỏ những sai số nhất thời như mây che ảnh vệ tinh để thấy xu hướng sinh trưởng cốt lõi.',
          detail: 'Ảnh vệ tinh MODIS thường bị ảnh hưởng bởi mây trong mùa mưa ở ĐBSCL. Rolling mean 7 ngày giúp "làm phẳng" những gián đoạn này.',
          danger: 'Khi rolling mean giảm liên tục 3–5 ngày: xu hướng suy giảm thực sự, không phải nhiễu vệ tinh.',
          tip: 'Đặc biệt quan trọng vào mùa mưa (tháng 5–11) khi tần suất mây che cao.',
        },
        {
          key: 'lst', label: 'LST', unit: '[°C]', icon: 'ti-temperature-sun',
          importance: null, rank: null, short: 'Nhiệt độ bề mặt đất (Land Surface Temp)',
          desc: 'Nhiệt độ bề mặt đất đo từ vệ tinh MODIS (MOD11A1). Phản ánh mức độ "nóng" của đất và tán cây, tách biệt với nhiệt độ không khí.',
          detail: 'LST cao hơn bình thường cho thấy thoát hơi nước kém (cây stress không mở khí khổng) hoặc đất đang khô nứt.',
          danger: 'LST > 45°C vào ban ngày: ngưỡng nhiệt độ gây stress nhiệt trực tiếp cho lúa.',
          tip: 'LST có thể cao hơn nhiệt độ không khí 5–15°C trên đất trống hoặc cây bị stress.',
        },
        {
          key: 'lst_ndvi_ratio', label: 'LST/NDVI ratio', unit: '[°C/index]', icon: 'ti-flame',
          importance: 38.3, rank: 7, short: 'Tỉ lệ nhiệt độ / sức khỏe cây',
          desc: 'Tỉ lệ giữa nhiệt độ bề mặt và chỉ số thực vật. Chỉ số tổng hợp: khi LST cao và NDVI thấp đồng thời (tỉ lệ rất lớn), cây đang chịu stress kép.',
          detail: 'Feature xếp hạng #7 theo XGBoost gain (38.3). Khi ratio này tăng đột biến, thường là dấu hiệu đất mất nước nghiêm trọng.',
          danger: 'Ratio > 80: cây đang trong tình trạng stress nhiệt-hạn kép nghiêm trọng.',
          tip: 'Tính bằng: LST (K) / max(NDVI, 0.01) để tránh chia cho 0.',
        },
      ],
    },
    {
      id: 'salinity',
      icon: 'ti-droplet',
      label: 'Độ mặn',
      emoji: '🌊',
      color: '#D97706',
      colorLight: 'color-mix(in srgb, #D97706 12%, var(--surface))',
      colorBorder: 'color-mix(in srgb, #D97706 30%, var(--border))',
      colorGlow: 'rgba(217,119,6,.18)',
      colorGlowStrong: 'rgba(217,119,6,.35)',
      summary: 'Đo lường trực tiếp "kẻ thù" của cây trồng: nồng độ muối xâm nhập từ các nhánh sông Mekong qua cửa biển.',
      features: [
        {
          key: 'salinity_psu', label: 'Salinity PSU', unit: '[PSU / ‰]', icon: 'ti-droplet-half-2',
          importance: null, rank: null, short: 'Nồng độ muối trong nước',
          desc: 'Nồng độ muối trong nước (Practical Salinity Unit — tương đương phần ngàn ‰). Đây là yếu tố quyết định nhất đối với sức khỏe cây trồng tại vùng ven biển ĐBSCL.',
          detail: 'Tuy nhiên, mô hình KHÔNG chỉ phụ thuộc vào salinity — feature importance cho thấy NDVI tendency quan trọng hơn nhiều.',
          danger: '≥ 1 PSU: lúa bắt đầu bị ảnh hưởng. ≥ 4 PSU: lúa bắt đầu chết. ≥ 8 PSU: cây không thể sống sót.',
          tip: 'Nước biển trung bình 35 PSU. Nước uống được < 0.5 PSU. Mục tiêu bảo vệ lúa: < 1 PSU.',
        },
        {
          key: 'salinity_7d_avg', label: 'Salinity 7d avg', unit: '[PSU]', icon: 'ti-chart-dots',
          importance: null, rank: null, short: 'Độ mặn trung bình 7 ngày',
          desc: 'Trung bình độ mặn trong 7 ngày qua. Phản ánh mức độ phơi nhiễm muối tích lũy của cây trồng và đất, quan trọng hơn giá trị ngay tức thì.',
          detail: 'Muối tích lũy trong đất theo thời gian. Một đợt mặn cao kéo dài 7 ngày gây tổn hại nhiều hơn đỉnh mặn 1 ngày cùng nồng độ.',
          danger: '7d avg > 3 PSU: đất đang tích lũy muối nguy hiểm dù đỉnh mặn đã qua.',
          tip: 'Kết hợp với salinity_tendency để nhận biết xu hướng: mặn đang tăng hay giảm?',
        },
        {
          key: 'salinity_7d_median', label: 'Salinity 7d median', unit: '[PSU]', icon: 'ti-math-function',
          importance: 26.8, rank: 10, short: 'Độ mặn trung vị 7 ngày — Top 10 feature',
          desc: 'Trung vị (median) độ mặn trong 7 ngày. Ít bị ảnh hưởng bởi đỉnh mặn bất thường hơn so với trung bình.',
          detail: 'Feature xếp hạng #10 theo XGBoost gain (26.8). Trung vị bền vững hơn trung bình trước outlier.',
          danger: 'Median > 4 PSU trong 7 ngày: mức độ mặn nền đã vượt ngưỡng gây hại cây trồng.',
          tip: 'Sự chênh lệch lớn giữa mean và median của salinity gợi ý có đỉnh mặn bất thường cần xem xét.',
        },
        {
          key: 'salinity_tendency', label: 'Salinity tendency', unit: '[ΔPSU/ngày]', icon: 'ti-trending-up',
          importance: null, rank: null, short: 'Xu hướng thay đổi độ mặn',
          desc: 'Tốc độ thay đổi nồng độ muối theo thời gian. Giá trị dương: mặn đang tăng (xâm nhập vào). Giá trị âm: mặn đang rút.',
          detail: 'Xu hướng quan trọng không kém giá trị tuyệt đối. Mặn 3 PSU đang tăng nhanh nguy hiểm hơn mặn 5 PSU đang giảm.',
          danger: 'Tendency > +0.5 PSU/ngày: mặn đang tăng rất nhanh, có thể do triều cường.',
          tip: 'Theo dõi salinity_tendency kết hợp với dự báo thủy triều để chuẩn bị đóng cống kịp thời.',
        },
      ],
    },
    {
      id: 'climate',
      icon: 'ti-cloud-rain',
      label: 'Khí hậu',
      emoji: '🌤️',
      color: '#1A8898',
      colorLight: 'color-mix(in srgb, #1A8898 12%, var(--surface))',
      colorBorder: 'color-mix(in srgb, #1A8898 30%, var(--border))',
      colorGlow: 'rgba(26,136,152,.18)',
      colorGlowStrong: 'rgba(26,136,152,.35)',
      summary: 'Theo dõi các yếu tố thời tiết cực đoan ảnh hưởng đến bốc hơi nước và sự tích tụ muối trong đất.',
      features: [
        {
          key: 'temp_mean', label: 'Nhiệt độ TB', unit: '[°C]', icon: 'ti-temperature',
          importance: null, rank: null, short: 'Nhiệt độ không khí trung bình ngày',
          desc: 'Nhiệt độ không khí trung bình ngày (°C). Nhiệt độ cao làm tăng bốc hơi nước từ đất và thoát hơi nước từ cây, khiến nồng độ muối trong đất tăng lên.',
          detail: 'Ở ĐBSCL, nhiệt độ mùa khô (tháng 1–4) trung bình 28–34°C, đẩy mạnh bốc thoát hơi nước nội đồng trong khi lưu lượng sông giảm.',
          danger: 'Nhiệt độ TB > 35°C kéo dài: tăng tốc bốc hơi nước, cô đặc muối trong lớp đất mặt.',
          tip: 'Kết hợp với temp_max và heatwave_consecutive_days để đánh giá mức độ stress nhiệt tổng thể.',
        },
        {
          key: 'temp_max', label: 'Nhiệt độ max', unit: '[°C]', icon: 'ti-temperature-plus',
          importance: null, rank: null, short: 'Nhiệt độ cao nhất trong ngày',
          desc: 'Nhiệt độ không khí cao nhất trong ngày (°C). Đỉnh nhiệt độ gây stress trực tiếp cho quá trình quang hợp và thoát hơi nước của cây.',
          detail: 'Lúa bắt đầu bị stress nhiệt khi nhiệt độ > 35°C trong giai đoạn trổ bông.',
          danger: 'Temp_max > 38°C: phấn hoa lúa bị chết, năng suất giảm mạnh dù không có mặn.',
          tip: 'Chênh lệch lớn giữa temp_max và temp_min cho thấy bức xạ mặt trời cao.',
        },
        {
          key: 'precipitation', label: 'Lượng mưa', unit: '[mm/ngày]', icon: 'ti-cloud-rain',
          importance: null, rank: null, short: 'Lượng mưa trong ngày',
          desc: 'Lượng mưa trong ngày (mm). Mưa nhiều giúp "rửa mặn" cho đất và cung cấp nước ngọt pha loãng nồng độ muối trong kênh rạch.',
          detail: 'Tại Bến Tre, mùa mưa (tháng 5–11) có lượng mưa 100–300mm/tháng giúp đẩy lùi mặn tự nhiên.',
          danger: 'Không mưa liên tục > 10 ngày trong mùa khô: mặn tích lũy nghiêm trọng.',
          tip: 'precip_7d_sum và precip_30d_sum cho biết "hồ nước dự trữ" tự nhiên của hệ sinh thái.',
        },
        {
          key: 'precip_7d_sum', label: 'Mưa 7 ngày', unit: '[mm]', icon: 'ti-droplets',
          importance: null, rank: null, short: 'Tổng lượng mưa 7 ngày',
          desc: 'Tổng lượng mưa tích lũy trong 7 ngày qua (mm). Phản ánh khả năng "rửa mặn" và bổ sung độ ẩm đất trong tuần vừa qua.',
          detail: 'precip_7d_sum cân bằng giữa mưa lớn 1 ngày và mưa rải đều 7 ngày về hiệu quả duy trì độ ẩm.',
          danger: 'precip_7d_sum < 10mm trong mùa trồng: đất mất đi lớp bảo vệ độ ẩm, muối bốc lên mặt đất.',
          tip: 'Ngưỡng tham khảo: lúa cần tối thiểu 3–5mm nước/ngày để duy trì sức sống.',
        },
        {
          key: 'et0', label: 'ET0', unit: '[mm/ngày]', icon: 'ti-wave-sine',
          importance: null, rank: null, short: 'Bốc thoát hơi nước tham chiếu',
          desc: 'Evapotranspiration tham chiếu (mm/ngày) — lượng nước mà một bề mặt cây trồng chuẩn sẽ thoát ra trong điều kiện lý tưởng.',
          detail: 'ET0 tính theo công thức Penman-Monteith từ nhiệt độ, bức xạ, gió, độ ẩm. Cao vào mùa khô (4–6mm/ngày), thấp vào mùa mưa (2–4mm/ngày).',
          danger: 'ET0 > 6mm/ngày mà không có mưa bù: đất mất nước rất nhanh, muối cô đặc trong lớp rễ.',
          tip: 'ET0 là input để tính moisture_deficit — một trong những chỉ số tổng hợp quan trọng.',
        },
      ],
    },
    {
      id: 'soil',
      icon: 'ti-plant',
      label: 'Đất & Thổ nhưỡng',
      emoji: '🌱',
      color: '#7C3AED',
      colorLight: 'color-mix(in srgb, #7C3AED 12%, var(--surface))',
      colorBorder: 'color-mix(in srgb, #7C3AED 30%, var(--border))',
      colorGlow: 'rgba(124,58,237,.18)',
      colorGlowStrong: 'rgba(124,58,237,.35)',
      summary: 'Điều kiện đất về độ ẩm, nhiệt độ và các chỉ số tổng hợp phản ánh tình trạng nước-muối trong lớp rễ cây.',
      features: [
        {
          key: 'soil_moisture_surface', label: 'SM surface', unit: '[m³/m³]', icon: 'ti-droplet-filled',
          importance: null, rank: null, short: 'Độ ẩm đất lớp mặt (0–7cm)',
          desc: 'Thể tích nước trên thể tích đất ở lớp mặt 0–7cm (m³/m³). Khi đất quá khô, muối từ lớp sâu bốc lên mặt đất qua mao dẫn.',
          detail: 'Dữ liệu từ ERA5-Land. Độ ẩm đất tối ưu cho lúa: 0.30–0.45 m³/m³.',
          danger: 'Soil_moisture < 0.15 m³/m³: cây bắt đầu héo vĩnh viễn nếu không được tưới kịp thời.',
          tip: 'Kết hợp với salinity_psu: đất ướt + mặn cao ít nguy hiểm hơn đất khô + mặn thấp.',
        },
        {
          key: 'soil_temp', label: 'Nhiệt đất', unit: '[°C]', icon: 'ti-thermometer',
          importance: null, rank: null, short: 'Nhiệt độ đất',
          desc: 'Nhiệt độ trong lớp đất (°C). Ảnh hưởng trực tiếp đến hoạt động của vi sinh vật đất, tốc độ phân giải hữu cơ, và khả năng hút dinh dưỡng của rễ cây.',
          detail: 'Đất nóng thúc đẩy quá trình bốc hơi nước từ đất (soil evaporation), làm cô đặc muối ở lớp mặt.',
          danger: 'Soil_temp > 38°C: enzyme rễ bị biến tính, khả năng chống chịu mặn giảm đáng kể.',
          tip: 'Soil_temp thường thấp hơn nhiệt độ không khí 3–8°C nhờ che phủ thực vật.',
        },
        {
          key: 'heatwave_consecutive_days', label: 'Nắng nóng', unit: '[ngày]', icon: 'ti-sun-high',
          importance: null, rank: null, short: 'Số ngày nắng nóng liên tiếp',
          desc: 'Số ngày liên tiếp có nhiệt độ cao vượt ngưỡng (heatwave). Theo dõi tích lũy stress nhiệt — không phải đỉnh mà là độ kéo dài.',
          detail: 'Cây trồng có khả năng hồi phục từ 1–2 ngày nóng cao điểm, nhưng 7+ ngày liên tiếp gây tổn thương tích lũy.',
          danger: 'Heatwave > 10 ngày liên tiếp: stress nhiệt kép với mặn có thể gây thiệt hại mùa vụ hoàn toàn.',
          tip: 'Đặc biệt nguy hiểm khi trùng với giai đoạn lúa trổ bông (mẫn cảm nhất với nhiệt).',
        },
        {
          key: 'days_without_rain', label: 'Không mưa', unit: '[ngày]', icon: 'ti-cloud-off',
          importance: null, rank: null, short: 'Số ngày liên tiếp không có mưa',
          desc: 'Số ngày liên tiếp không có lượng mưa đáng kể. Chỉ số hạn nông nghiệp đơn giản nhưng hiệu quả.',
          detail: 'Mỗi ngày không mưa, đất mất nước và muối tích lũy thêm. Sau 5 ngày không mưa trong mùa khô, lớp đất mặt thường khô hoàn toàn.',
          danger: 'days_without_rain > 20 trong mùa khô: cần can thiệp tưới tiêu chủ động ngay.',
          tip: 'Kết hợp với is_dry_season: cùng số ngày không mưa, mùa khô nguy hiểm gấp 3–5 lần mùa mưa.',
        },
      ],
    },
    {
      id: 'location',
      icon: 'ti-map-pin',
      label: 'Vị trí & Thời gian',
      emoji: '📍',
      color: '#6366F1',
      colorLight: 'color-mix(in srgb, #6366F1 12%, var(--surface))',
      colorBorder: 'color-mix(in srgb, #6366F1 30%, var(--border))',
      colorGlow: 'rgba(99,102,241,.18)',
      colorGlowStrong: 'rgba(99,102,241,.35)',
      summary: 'Bối cảnh không gian địa lý và chu kỳ mùa vụ giúp mô hình dự báo chính xác theo đặc thù từng vị trí và mùa.',
      features: [
        {
          key: 'lat', label: 'Vĩ độ (Lat)', unit: '[°N]', icon: 'ti-map-2',
          importance: 92.2, rank: 3, short: 'Vĩ độ địa lý — Top 3 feature',
          desc: 'Vĩ độ địa lý của trạm quan trắc (độ Bắc). Trong bối cảnh ĐBSCL, vĩ độ là proxy cho vị trí bắc-nam: trạm phía nam (vĩ độ thấp như Thạnh Phú ~9.9°N) gần biển hơn.',
          detail: 'Feature xếp hạng #3 (gain 92.2) — cao hơn cả salinity trong nhiều trường hợp.',
          danger: 'Trạm vĩ độ thấp (9.9–10.1°N) trong vùng Bến Tre: luôn có nguy cơ mặn cao hơn cơ bản.',
          tip: 'Lat + Lon + distance_to_estuary tạo thành "bộ 3 địa lý" — cùng nhau explain ~30% gain của mô hình.',
        },
        {
          key: 'lon', label: 'Kinh độ (Lon)', unit: '[°E]', icon: 'ti-map-2',
          importance: 80.0, rank: 4, short: 'Kinh độ địa lý — Top 4 feature',
          desc: 'Kinh độ địa lý của trạm quan trắc (độ Đông). Trong vùng Bến Tre, kinh độ phản ánh vị trí đông-tây.',
          detail: 'Feature xếp hạng #4 (gain 80.0). Kinh độ cao trong vùng Bến Tre = gần biển Đông = mặn sớm hơn mùa khô.',
          danger: 'Trạm kinh độ > 106.7°E (như Bình Đại): cần theo dõi từ đầu mùa khô (tháng 12).',
          tip: 'Bình Đại (106.79°E, 8.3km cửa biển) vs Châu Thành (106.43°E, 38.1km) — khác nhau rõ rệt về nguy cơ.',
        },
        {
          key: 'distance_to_estuary_km', label: 'Dist to mouth', unit: '[km]', icon: 'ti-current-location',
          importance: 53.8, rank: 6, short: 'Khoảng cách đến cửa biển — Top 6',
          desc: 'Khoảng cách từ trạm quan trắc đến cửa biển gần nhất (km). Chỉ số địa lý trực tiếp nhất về mức độ phơi nhiễm với nước biển.',
          detail: 'Feature xếp hạng #6 (gain 53.8). Thạnh Phú (5.2km), Bình Đại (8.3km), Ba Tri (22.5km), Giồng Trôm (29.6km), Châu Thành (38.1km).',
          danger: 'Distance < 10km: mặn xâm nhập ngay trong đêm triều cường đầu tiên của mùa khô.',
          tip: 'Nên thiết lập hệ thống cảnh báo sớm hơn 2–3 tuần tại các trạm gần cửa biển.',
        },
        {
          key: 'day_of_year', label: 'Ngày trong năm', unit: '[1–366]', icon: 'ti-calendar-event',
          importance: 27.3, rank: 9, short: 'Chu kỳ mùa vụ theo ngày — Top 9',
          desc: 'Số thứ tự ngày trong năm (Day of Year, 1–366). Giúp mô hình nhận biết đang ở chu kỳ nào của tự nhiên.',
          detail: 'Feature xếp hạng #9 (gain 27.3). Mô hình học được rằng: ngày 30–120 (tháng 1–4) = đỉnh mùa khô, nguy cơ cao nhất.',
          danger: 'Ngày 60–90 (tháng 3): đỉnh cao nhất của mùa hạn mặn tại Bến Tre lịch sử.',
          tip: 'Kết hợp với month_sin và month_cos để encode tính chu kỳ tốt hơn.',
        },
        {
          key: 'is_dry_season', label: 'Mùa khô', unit: '[0/1]', icon: 'ti-sun',
          importance: null, rank: null, short: 'Đang trong mùa khô không?',
          desc: 'Biến nhị phân: 1 = đang là mùa khô (tháng 12, 1, 2, 3, 4), 0 = mùa mưa.',
          detail: 'Feature binary đơn giản nhưng mang thông tin mùa vụ rất quan trọng. Trong mùa khô: lưu lượng Mekong giảm 60–80% so với mùa mưa.',
          danger: 'is_dry_season = 1 kết hợp salinity_psu > 2: mức độ nguy hiểm tăng đáng kể.',
          tip: 'Năm 2020 là đợt hạn mặn lịch sử ĐBSCL — tất cả trạm ven biển đều báo DANGER tháng 3/2020.',
        },
      ],
    },
  ];

  /* anchor map */
  const FEATURE_MAP = {};
  FEATURE_GROUPS_DATA.forEach(g => {
    g.features.forEach(f => { FEATURE_MAP[f.key] = { groupId: g.id, feature: f }; });
  });
  MS.FEATURE_ENCYCLOPEDIA = FEATURE_GROUPS_DATA;
  MS.FEATURE_MAP = FEATURE_MAP;

  /* ══════════════════════════════════════════════
     ANIMATED IMPORTANCE BAR
  ══════════════════════════════════════════════ */
  function ImportanceBadge({ importance, rank }) {
    if (!importance) return null;
    return (
      <span className="fp-importance-badge">
        <i className="ti ti-trophy" style={{ fontSize: '9px' }} />
        #{rank} · gain {importance}
      </span>
    );
  }

  /* Animating bar that triggers on mount */
  function ImportanceBar({ importance, maxImportance = 245, color, showValue = true }) {
    const [width, setWidth] = useState(0);
    useEffect(() => {
      const t = setTimeout(() => setWidth((importance / maxImportance) * 100), 80);
      return () => clearTimeout(t);
    }, [importance]);
    return (
      <div className="fp-imp-track">
        <div
          className="fp-imp-fill"
          style={{
            width: `${width}%`,
            background: `linear-gradient(90deg, ${color}99, ${color})`,
            transition: 'width 1.1s cubic-bezier(.16,1,.3,1)',
          }}
        />
        {showValue && (
          <span className="fp-imp-val" style={{ color }}>{importance}</span>
        )}
      </div>
    );
  }

  /* ══════════════════════════════════════════════
     SPARKLE PARTICLES on card expand
  ══════════════════════════════════════════════ */
  function Sparkles({ color, active }) {
    const particles = [
      { x: '15%', y: '-8px',  delay: 0,    size: 4 },
      { x: '50%', y: '-12px', delay: 60,   size: 3 },
      { x: '80%', y: '-7px',  delay: 120,  size: 5 },
      { x: '30%', y: '-10px', delay: 40,   size: 3 },
      { x: '70%', y: '-9px',  delay: 90,   size: 4 },
    ];
    if (!active) return null;
    return (
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, pointerEvents: 'none', overflow: 'visible', height: 0 }}>
        {particles.map((p, i) => (
          <div key={i} style={{
            position: 'absolute',
            left: p.x,
            top: p.y,
            width: p.size,
            height: p.size,
            borderRadius: '50%',
            background: color,
            animation: `fp-spark .55s ${p.delay}ms var(--ease) both`,
          }} />
        ))}
      </div>
    );
  }

  /* ══════════════════════════════════════════════
     FEATURE CARD — rich hover + expand animation
  ══════════════════════════════════════════════ */
  function FeatureCard({ feature, group, isHighlighted, cardRef, index, collapseSignal }) {
    const [open, setOpen] = useState(isHighlighted);
    const [hovered, setHovered] = useState(false);
    const [justOpened, setJustOpened] = useState(false);
    const [visible, setVisible] = useState(false);
    const innerRef = useRef(null);

    /* Staggered entrance */
    useEffect(() => {
      const t = setTimeout(() => setVisible(true), index * 55);
      return () => clearTimeout(t);
    }, []);

    useEffect(() => { if (isHighlighted) setOpen(true); }, [isHighlighted]);
    useEffect(() => { if (!isHighlighted) setOpen(false); }, [collapseSignal]);

    const handleToggle = useCallback(() => {
      const opening = !open;
      setOpen(opening);
      if (opening) {
        setJustOpened(true);
        setTimeout(() => setJustOpened(false), 700);
      }
    }, [open]);

    const isTop = feature.rank && feature.rank <= 3;

    return (
      <div
        ref={cardRef}
        id={`feat-${feature.key}`}
        className="fp-feat-card"
        style={{
          '--fc-color': group.color,
          '--fc-glow': group.colorGlow,
          '--fc-glow-strong': group.colorGlowStrong,
          border: isHighlighted
            ? `2px solid ${group.color}`
            : hovered
              ? `1.5px solid ${group.colorBorder}`
              : '1px solid var(--border)',
          background: isHighlighted ? group.colorLight : 'var(--surface)',
          boxShadow: isHighlighted
            ? `0 0 0 2px ${group.colorGlow}, var(--sh-sm)`
            : hovered
              ? `0 3px 12px ${group.colorGlow}, var(--sh-sm)`
              : 'var(--sh-xs)',
          transform: visible
            ? hovered ? 'translateY(-2px) scale(1.005)' : 'translateY(0) scale(1)'
            : 'translateY(12px)',
          opacity: visible ? 1 : 0,
          transition: [
            'transform .28s var(--ease)',
            'box-shadow .28s var(--ease)',
            'border-color .2s',
            'background .2s',
            'opacity .4s var(--ease)',
          ].join(', '),
          borderRadius: 'var(--r-lg)',
          marginBottom: '10px',
          overflow: 'visible',
          position: 'relative',
          cursor: 'pointer',
        }}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        {/* Top-ranked shimmer border */}
        {isTop && (
          <div style={{
            position: 'absolute', inset: 0,
            borderRadius: 'var(--r-lg)',
            background: `linear-gradient(90deg, transparent, ${group.color}22, transparent)`,
            backgroundSize: '200% 100%',
            animation: 'fp-shimmer 2.4s ease infinite',
            pointerEvents: 'none',
          }} />
        )}

        {/* Sparkles on open */}
        <Sparkles color={group.color} active={justOpened} />

        {/* Card header */}
        <button
          className="fp-feat-header"
          onClick={handleToggle}
          style={{ borderRadius: open ? `var(--r-lg) var(--r-lg) 0 0` : 'var(--r-lg)' }}
        >
          {/* Icon */}
          <div className="fp-feat-icon" style={{
            background: group.colorLight,
            border: `1.5px solid ${hovered ? group.color : group.colorBorder}`,
            boxShadow: hovered ? `0 0 0 3px ${group.colorGlow}` : 'none',
            transition: 'border-color .2s, box-shadow .2s',
          }}>
            <i className={`ti ${feature.icon}`} style={{ fontSize: '16px', color: group.color }} />
          </div>

          {/* Labels */}
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '7px', flexWrap: 'wrap', marginBottom: '2px' }}>
              <span className="fp-feat-key">{feature.label}</span>
              <span className="fp-feat-unit">{feature.unit}</span>
              <ImportanceBadge importance={feature.importance} rank={feature.rank} />
              {isTop && (
                <span style={{
                  fontSize: '9px', padding: '1px 6px', borderRadius: 'var(--r-full)',
                  background: group.colorLight, color: group.color,
                  border: `1px solid ${group.colorBorder}`,
                  fontFamily: 'var(--ff-mono)', fontWeight: 700,
                  animation: 'fp-pulse-badge 2s ease infinite',
                }}>
                  ✦ TOP {feature.rank}
                </span>
              )}
            </div>
            <div className="fp-feat-short">{feature.short}</div>

            {/* Inline importance bar (always visible if ranked) */}
            {feature.importance && !open && (
              <div style={{ marginTop: '6px' }}>
                <ImportanceBar importance={feature.importance} color={group.color} />
              </div>
            )}
          </div>

          {/* Chevron */}
          <div style={{
            transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
            transition: 'transform .3s var(--ease)',
            color: open ? group.color : 'var(--ink-4)',
            flexShrink: 0,
          }}>
            <i className="ti ti-chevron-down" style={{ fontSize: '15px' }} />
          </div>
        </button>

        {/* Expanded body */}
        <div ref={innerRef} className="fp-feat-body" style={{
          maxHeight: open ? '600px' : '0',
          opacity: open ? 1 : 0,
          overflow: 'hidden',
          transition: 'max-height .45s cubic-bezier(.16,1,.3,1), opacity .3s ease',
          borderTop: open ? `1px solid color-mix(in srgb, ${group.color} 20%, var(--border))` : 'none',
        }}>
          <div style={{ padding: '14px 16px 16px' }}>

            {/* Importance bar full (inside expanded) */}
            {feature.importance && (
              <div style={{ marginBottom: '14px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '5px' }}>
                  <span style={{ fontFamily: 'var(--ff-mono)', fontSize: '10px', color: 'var(--ink-4)', textTransform: 'uppercase', letterSpacing: '.06em' }}>
                    XGBoost Gain Score
                  </span>
                  <span style={{ fontFamily: 'var(--ff-mono)', fontSize: '11px', fontWeight: 700, color: group.color }}>{feature.importance}</span>
                </div>
                <ImportanceBar importance={feature.importance} color={group.color} showValue={false} />
              </div>
            )}

            {/* Description */}
            <p className="fp-feat-desc">{feature.desc}</p>

            {/* Detail box */}
            <div className="fp-detail-box">
              <div className="fp-detail-label">
                <i className="ti ti-info-circle" style={{ fontSize: '11px' }} /> Chi tiết kỹ thuật
              </div>
              <p className="fp-detail-text">{feature.detail}</p>
            </div>

            {/* Danger + Tip grid */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <div className="fp-danger-box" style={{
                background: `color-mix(in srgb, #C82020 8%, var(--surface))`,
                border: `1px solid color-mix(in srgb, #C82020 25%, var(--border))`,
              }}>
                <div className="fp-box-label" style={{ color: '#C82020' }}>
                  <i className="ti ti-alert-triangle" style={{ fontSize: '11px' }} /> Ngưỡng nguy hiểm
                </div>
                <p className="fp-box-text">{feature.danger}</p>
              </div>
              <div className="fp-tip-box" style={{
                background: `color-mix(in srgb, ${group.color} 8%, var(--surface))`,
                border: `1px solid color-mix(in srgb, ${group.color} 25%, var(--border))`,
              }}>
                <div className="fp-box-label" style={{ color: group.color }}>
                  <i className="ti ti-bulb" style={{ fontSize: '11px' }} /> Gợi ý phân tích
                </div>
                <p className="fp-box-text">{feature.tip}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  /* ══════════════════════════════════════════════
     GROUP SECTION — hover glow on entire group
  ══════════════════════════════════════════════ */
  function GroupSection({ group, highlightKey, highlightRef, index, collapseSignal }) {
    const [hovered, setHovered] = useState(false);
    const [visible, setVisible] = useState(false);

    useEffect(() => {
      const t = setTimeout(() => setVisible(true), index * 120);
      return () => clearTimeout(t);
    }, []);

    return (
      <section
        id={`group-${group.id}`}
        style={{
          marginBottom: '40px',
          opacity: visible ? 1 : 0,
          transform: visible ? 'translateY(0)' : 'translateY(18px)',
          transition: 'opacity .5s var(--ease), transform .5s var(--ease)',
        }}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        {/* Group header */}
        <div
          className="fp-group-header"
          style={{
            borderBottom: `2px solid ${group.color}`,
            marginBottom: '16px',
            paddingBottom: '14px',
            background: hovered
              ? `linear-gradient(135deg, ${group.colorLight} 0%, transparent 60%)`
              : 'transparent',
            borderRadius: hovered ? 'var(--r-md) var(--r-md) 0 0' : '0',
            padding: hovered ? '14px 14px 14px' : '0 0 14px 0',
            transition: 'background .35s ease, padding .3s ease, border-radius .3s ease',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            {/* Animated emoji icon */}
            <div
              className="fp-group-icon"
              style={{
                background: group.colorLight,
                border: `2px solid ${hovered ? group.color : group.colorBorder}`,
                boxShadow: hovered ? `0 0 0 3px ${group.colorGlow}, var(--sh-sm)` : 'var(--sh-xs)',
                transform: hovered ? 'rotate(-2deg) scale(1.03)' : 'rotate(0deg) scale(1)',
                transition: 'all .35s var(--ease)',
              }}
            >
              <span style={{ fontSize: '20px', display: 'block', lineHeight: 1 }}>{group.emoji}</span>
            </div>

            <div>
              <div style={{
                fontFamily: 'var(--ff-heading)', fontSize: '20px', fontWeight: 700,
                color: group.color,
                display: 'flex', alignItems: 'center', gap: '8px',
                transition: 'letter-spacing .3s ease',
                letterSpacing: hovered ? '.01em' : '0',
              }}>
                <i className={`ti ${group.icon}`} />
                Nhóm {group.label}
                <span className="fp-group-count" style={{
                  background: group.colorLight,
                  border: `1px solid ${group.colorBorder}`,
                  color: group.color,
                }}>
                  {group.features.length} features
                </span>
              </div>
              <div style={{
                fontFamily: 'var(--ff-body)', fontSize: '12.5px',
                color: hovered ? 'var(--ink-2)' : 'var(--ink-3)',
                marginTop: '3px',
                transition: 'color .2s',
              }}>
                {group.summary}
              </div>
            </div>
          </div>

          {/* Feature mini dots - visual indicator of how many features */}
          <div style={{ display: 'flex', gap: '4px', marginTop: '10px', paddingLeft: '52px' }}>
            {group.features.map((f, i) => (
              <div key={f.key} style={{
                width: f.importance ? '14px' : '8px',
                height: '4px',
                borderRadius: '2px',
                background: f.importance ? group.color : group.colorBorder,
                opacity: hovered ? 1 : 0.6,
                transition: `opacity .2s ${i * 40}ms, width .3s var(--ease)`,
              }} title={f.label} />
            ))}
          </div>
        </div>

        {/* Feature cards */}
        {group.features.map((f, i) => (
          <FeatureCard
                key={f.key}
                feature={f}
                group={group}
                isHighlighted={f.key === highlightKey}
                cardRef={f.key === highlightKey ? highlightRef : null}
                index={i}
                collapseSignal={collapseSignal}
              />
        ))}
      </section>
    );
  }


  /* ══════════════════════════════════════════════
     LEFT SIDEBAR NAV — stn-card–style hover effects
     Dùng CSS class .fp-sidenav-item + --fp-nav-clr
     để mirror đúng pattern của .stn-card:
       ::before accent bar, translateX, glow ring, dot pulse
  ══════════════════════════════════════════════ */
  function SideNav({ groups, activeGroup, onSelect, highlightFeature, onClearHighlight }) {
    return (
      <div className="fp-sidenav">
        <div className="fp-sidenav-title">
          <i className="ti ti-category" /> Nhóm đặc trưng
        </div>

        {groups.map((g, i) => {
          const isActive = activeGroup === g.id;
          return (
            <div
              key={g.id}
              /* class: fp-sidenav-item + active — tất cả hover logic nằm trong CSS */
              className={`fp-sidenav-item${isActive ? ' active' : ''}`}
              style={{
                /* CSS variable cho màu accent của từng nhóm */
                '--fp-nav-clr': g.color,
                animationDelay: `${i * 60}ms`,
              }}
              onClick={() => {
                onSelect(g.id);
                if (onClearHighlight) onClearHighlight();
                const el = document.getElementById(`group-${g.id}`);
                if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
              }}
            >
              {/* Icon — class fp-nav-icon để CSS transition color + scale */}
              <i className={`ti ${g.icon} fp-nav-icon`} />

              {/* Text block */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="fp-nav-label">{g.label}</div>
                <div className="fp-nav-sub">{g.features.length} features</div>
              </div>

              {/* Feature dots — fp-nav-dot + is-top để CSS stagger pulse */}
              <div className="fp-nav-dots">
                {g.features.slice(0, 4).map(f => (
                  <div
                    key={f.key}
                    className={`fp-nav-dot${f.importance ? ' is-top' : ''}`}
                    style={{
                      background: f.importance ? g.color : g.colorBorder,
                    }}
                  />
                ))}
              </div>
            </div>
          );
        })}

        {/* Stats panel */}
        <div className="fp-sidenav-stats">
          <div className="fp-sidenav-stats-title">Tóm tắt mô hình</div>
          {[
            ['Tổng features', `${FEATURE_GROUPS_DATA.reduce((a,g)=>a+g.features.length,0)}`, 'var(--ink-2)'],
            ['Top feature', 'ndvi_tendency', 'var(--teal-5)'],
            ['Gain cao nhất', '245.1', 'var(--gold-6)'],
            ['PR-AUC', '0.974', '#0D9488'],
            ['F2 Score', '0.925', '#7C3AED'],
          ].map(([l, v, c]) => (
            <div key={l} className="fp-sidenav-stat-row">
              <span style={{ color: 'var(--ink-4)', fontFamily: 'var(--ff-body)' }}>{l}</span>
              <span style={{ color: c, fontFamily: 'var(--ff-mono)', fontWeight: 700, fontSize: '10.5px' }}>{v}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  function FeaturesPage({ highlightFeature, onClearHighlight }) {
    const [searchQ, setSearchQ] = useState('');
    const [pageVisible, setPageVisible] = useState(false);
    const [activeGroup, setActiveGroup] = useState(FEATURE_GROUPS_DATA[0]?.id || '');
    const [collapseSignal, setCollapseSignal] = useState(0);
    const highlightRef = useRef(null);

    useEffect(() => {
      const t = setTimeout(() => setPageVisible(true), 40);
      return () => clearTimeout(t);
    }, []);

    /* Scroll to highlighted feature */
    useEffect(() => {
      if (!highlightFeature) return;
      const found = MS.FEATURE_MAP[highlightFeature];
      if (found) setActiveGroup(found.groupId);
      setTimeout(() => {
        if (highlightRef.current) {
          highlightRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }, 260);
    }, [highlightFeature]);

    const filteredGroups = FEATURE_GROUPS_DATA.map(g => ({
      ...g,
      features: searchQ
        ? g.features.filter(f =>
            f.key.toLowerCase().includes(searchQ.toLowerCase()) ||
            f.label.toLowerCase().includes(searchQ.toLowerCase()) ||
            f.short.toLowerCase().includes(searchQ.toLowerCase()) ||
            (f.desc && f.desc.toLowerCase().includes(searchQ.toLowerCase()))
          )
        : g.features,
    })).filter(g => g.features.length > 0);

    const totalFeatures = FEATURE_GROUPS_DATA.reduce((a, g) => a + g.features.length, 0);
    const topFeatures = FEATURE_GROUPS_DATA.flatMap(g => g.features).filter(f => f.rank).sort((a, b) => a.rank - b.rank);

    return (
      <div style={{
        display: 'flex', height: 'calc(100vh - 50px)', overflow: 'hidden',
        opacity: pageVisible ? 1 : 0,
        transform: pageVisible ? 'translateY(0)' : 'translateY(10px)',
        transition: 'opacity .4s var(--ease), transform .4s var(--ease)',
      }}>

        {/* ── LEFT NAV ── */}
        <SideNav
          groups={FEATURE_GROUPS_DATA}
          activeGroup={activeGroup}
          onSelect={setActiveGroup}
          highlightFeature={highlightFeature}
          onClearHighlight={onClearHighlight}
        />

        {/* ── MAIN CONTENT ── */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '0 36px 48px' }}>

          {/* Hero header */}
          <div className="fp-hero">
            {highlightFeature && (
              <div
                className="fp-highlight-pill"
                onClick={() => { if (onClearHighlight) onClearHighlight(); setSearchQ(''); }}
              >
                <i className="ti ti-zoom-in" />
                Đang xem: <strong>{highlightFeature}</strong>
                <i className="ti ti-x" style={{ opacity: .6 }} />
              </div>
            )}

            <h1 className="fp-hero-title">
              <i className="ti ti-database-search" style={{ color: 'var(--teal-5)' }} />
              Đặc trưng đầu vào
              <span className="fp-hero-badge">
                {totalFeatures} features · 4 nhóm
              </span>
            </h1>
            <p className="fp-hero-sub">
              Giải thích chi tiết <strong>{totalFeatures} đặc trưng</strong> đầu vào của mô hình XGBoost, bao gồm
              ý nghĩa nông học, ngưỡng nguy hiểm, và vai trò trong dự báo xâm nhập mặn tại ĐBSCL.
            </p>

            {/* Top features quick-strip */}
            <div className="fp-topstrip">
              <span className="fp-topstrip-label">Top features:</span>
              {topFeatures.slice(0, 5).map(f => {
                const g = FEATURE_GROUPS_DATA.find(gr => gr.features.some(ff => ff.key === f.key));
                return (
                  <button
                    key={f.key}
                    className="fp-topstrip-chip"
                    style={{
                      '--chip-color': g?.color || 'var(--teal-5)',
                      '--chip-light': g?.colorLight || 'var(--teal-lt)',
                      '--chip-border': g?.colorBorder || 'var(--teal-bd)',
                    }}
                    onClick={() => {
                      const el = document.getElementById(`feat-${f.key}`);
                      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                      if (g) setActiveGroup(g.id);
                    }}
                  >
                    <span style={{ fontFamily: 'var(--ff-mono)', fontSize: '9px', opacity: .7 }}>#{f.rank}</span>
                    {f.label}
                  </button>
                );
              })}
            </div>

            {/* Search */}
            <div className="fp-search-wrap">
              <i className="ti ti-search fp-search-icon" />
              <input
                type="text"
                placeholder="Tìm feature (vd: ndvi, salinity, mưa...)"
                value={searchQ}
                onChange={e => setSearchQ(e.target.value)}
                className="fp-search-input"
              />
              {searchQ && (
                <button className="fp-search-clear" onClick={() => setSearchQ('')}>
                  <i className="ti ti-x" style={{ fontSize: '13px' }} />
                </button>
              )}
            </div>
            {searchQ && (
              <div style={{ marginTop: '8px', fontFamily: 'var(--ff-mono)', fontSize: '11px', color: 'var(--ink-4)' }}>
                {filteredGroups.reduce((a, g) => a + g.features.length, 0)} kết quả cho "{searchQ}"
              </div>
            )}
          </div>

          {/* Groups */}
          {filteredGroups.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--ink-4)' }}>
              <i className="ti ti-search-off" style={{ fontSize: '32px', opacity: .4, display: 'block', marginBottom: '12px' }} />
              <div style={{ fontFamily: 'var(--ff-body)', fontSize: '14px' }}>
                Không tìm thấy feature nào cho "{searchQ}"
              </div>
            </div>
          ) : (
            filteredGroups.map((g, i) => (
              <GroupSection
                key={g.id}
                group={g}
                highlightKey={highlightFeature}
                highlightRef={highlightRef}
                index={i}
                collapseSignal={collapseSignal}
              />
            ))
          )}
        </div>
      </div>
    );
  }

  MS.FeaturesPage = FeaturesPage;
}());
