"""One-time script: replaces the JS section of map.html with improved version."""
import os

MAP_FILE = os.path.join(os.path.dirname(__file__), '..', 'templates', 'map.html')

with open(MAP_FILE, 'r', encoding='utf-8') as f:
    content = f.read()

# Keep everything up to (including) the Bootstrap JS script tag
SPLIT_MARKER = '<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>'
idx = content.index(SPLIT_MARKER)
head = content[:idx]

new_tail = SPLIT_MARKER + """
  <script>
    let leafletMap = null;
    let clusterLayer = null;
    let plainLayer = null;
    let districtPolygons = [];
    let clusteringEnabled = true;

    const DISTRICT_BOUNDS = {
      "Bektemir":       [[41.265,69.330],[41.265,69.395],[41.310,69.395],[41.310,69.330]],
      "Chilonzor":      [[41.260,69.140],[41.260,69.215],[41.330,69.215],[41.330,69.140]],
      "Mirabad":        [[41.255,69.195],[41.255,69.260],[41.300,69.260],[41.300,69.195]],
      "Mirobod":        [[41.270,69.240],[41.270,69.295],[41.315,69.295],[41.315,69.240]],
      "Mirzo Ulug'bek": [[41.305,69.330],[41.305,69.400],[41.395,69.400],[41.395,69.330]],
      "Olmazor":        [[41.330,69.215],[41.330,69.295],[41.395,69.295],[41.395,69.215]],
      "Sergeli":        [[41.170,69.240],[41.170,69.340],[41.260,69.340],[41.260,69.240]],
      "Shayxontohur":   [[41.285,69.245],[41.285,69.305],[41.335,69.305],[41.335,69.245]],
      "Uchtepa":        [[41.285,69.150],[41.285,69.230],[41.365,69.230],[41.365,69.150]],
      "Yakkasaroy":     [[41.270,69.195],[41.270,69.245],[41.310,69.245],[41.310,69.195]],
      "Yashnobod":      [[41.215,69.270],[41.215,69.355],[41.275,69.355],[41.275,69.270]],
      "Yunusobod":      [[41.315,69.285],[41.315,69.375],[41.390,69.375],[41.390,69.285]]
    };
    const DISTRICT_COLORS = {
      "Bektemir":"#6366F1","Chilonzor":"#8B5CF6","Mirabad":"#EC4899","Mirobod":"#F43F5E",
      "Mirzo Ulug'bek":"#0EA5E9","Olmazor":"#10B981","Sergeli":"#F59E0B","Shayxontohur":"#14B8A6",
      "Uchtepa":"#F97316","Yakkasaroy":"#EF4444","Yashnobod":"#84CC16","Yunusobod":"#06B6D4"
    };

    function toggleClustering() {
      clusteringEnabled = !clusteringEnabled;
      document.getElementById('cluster-label').textContent = 'Klaster: ' + (clusteringEnabled ? 'ON' : 'OFF');
      if (clusterLayer) leafletMap.removeLayer(clusterLayer);
      if (plainLayer)   leafletMap.removeLayer(plainLayer);
      if (clusteringEnabled && clusterLayer) clusterLayer.addTo(leafletMap);
      if (!clusteringEnabled && plainLayer)  plainLayer.addTo(leafletMap);
    }

    function drawDistrictPolygons(selectedDistrict) {
      districtPolygons.forEach(p => leafletMap.removeLayer(p));
      districtPolygons = [];
      const entries = selectedDistrict
        ? Object.entries(DISTRICT_BOUNDS).filter(([k]) => k === selectedDistrict)
        : Object.entries(DISTRICT_BOUNDS);
      entries.forEach(([name, coords]) => {
        const color = DISTRICT_COLORS[name] || '#64748B';
        const poly = L.polygon(coords, {
          color: color, weight: 1.5, opacity: 0.55,
          fillColor: color, fillOpacity: 0.05, dashArray: '6,4'
        }).addTo(leafletMap);
        poly.bindTooltip('<b>' + name + '</b>', {permanent: false, direction: 'center'});
        districtPolygons.push(poly);
      });
    }

    async function loadMap() {
      try {
        const district = document.getElementById('district-select').value;
        let url = '/api/map-data';
        if (district) url += '?district=' + encodeURIComponent(district);
        const response = await fetch(url);
        const data = await response.json();
        if (!data || data.length === 0) {
          document.getElementById('map').innerHTML = '<div class="alert alert-warning m-3">Ma\\'lumot topilmadi</div>';
          return;
        }
        const total = data.length;
        const safe   = data.filter(d => d.Fault === 0).length;
        const warns  = data.filter(d => d.Fault === 1).length;
        const faults = data.filter(d => d.Fault === 2).length;

        document.getElementById('total-sensors').textContent = total;
        document.getElementById('safe-sensors').textContent  = safe;
        document.getElementById('warn-sensors').textContent  = warns;
        document.getElementById('fault-sensors').textContent = faults;
        document.getElementById('ss-total').textContent  = total;
        document.getElementById('ss-safe').textContent   = safe;
        document.getElementById('ss-warn').textContent   = warns;
        document.getElementById('ss-danger').textContent = faults;
        document.getElementById('avg-harorat').textContent    = (data.reduce((s,d)=>s+d.Harorat,0)/total).toFixed(1) + ' \u00b0C';
        document.getElementById('avg-chastota').textContent   = (data.reduce((s,d)=>s+d.Chastota,0)/total).toFixed(2) + ' Hz';
        document.getElementById('avg-kuchlanish').textContent = (data.reduce((s,d)=>s+d.Kuchlanish,0)/total).toFixed(0) + ' V';
        document.getElementById('avg-quvvat').textContent     = (data.reduce((s,d)=>s+d.Quvvat,0)/total).toFixed(2) + ' kW';

        document.getElementById('map-loading').style.display = 'none';
        document.getElementById('map-main').style.display    = 'block';

        if (!leafletMap) {
          leafletMap = L.map('map', {preferCanvas: true}).setView([41.2900, 69.2700], 11);
          L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
            attribution: '\u00a9 OpenStreetMap, \u00a9 CartoDB', subdomains: 'abcd', maxZoom: 19
          }).addTo(leafletMap);
        }

        if (clusterLayer) leafletMap.removeLayer(clusterLayer);
        if (plainLayer)   leafletMap.removeLayer(plainLayer);

        clusterLayer = L.markerClusterGroup({
          maxClusterRadius: 38,
          showCoverageOnHover: false,
          iconCreateFunction: function(cluster) {
            const children = cluster.getAllChildMarkers();
            const hasFault = children.some(m => m.options._fault === 2);
            const hasWarn  = children.some(m => m.options._fault === 1);
            const col = hasFault ? '#EF4444' : (hasWarn ? '#F59E0B' : '#10B981');
            const cnt = cluster.getChildCount();
            const sz  = cnt > 100 ? 44 : cnt > 30 ? 36 : 28;
            return L.divIcon({
              html: '<div style="width:' + sz + 'px;height:' + sz + 'px;border-radius:50%;background:' + col
                + ';display:flex;align-items:center;justify-content:center;color:white;font-weight:800;font-size:'
                + (sz > 36 ? 13 : 11) + 'px;box-shadow:0 2px 8px rgba(0,0,0,0.25);border:2px solid rgba(255,255,255,0.85);">'
                + cnt + '</div>',
              className: '', iconSize: [sz, sz]
            });
          }
        });
        plainLayer = L.layerGroup();

        data.forEach(d => {
          const col   = d.Fault === 2 ? '#EF4444' : (d.Fault === 1 ? '#F59E0B' : '#10B981');
          const slabel = d.Fault === 2
            ? '<span style="color:#EF4444;font-weight:700;">&#x1F534; MUAMMO</span>'
            : d.Fault === 1
              ? '<span style="color:#F59E0B;font-weight:700;">&#x1F7E1; OGOHLANTIRISH</span>'
              : '<span style="color:#10B981;font-weight:700;">&#x1F7E2; HAVFSIZ</span>';
          const popup = '<div style="min-width:195px;font-family:Inter,sans-serif;line-height:1.55;">'
            + '<div style="font-weight:800;font-size:0.93rem;color:#0F172A;margin-bottom:2px;">' + d.SensorID + '</div>'
            + '<div style="font-size:0.77rem;color:#64748B;margin-bottom:8px;">' + d.District + '</div>'
            + '<div style="font-size:0.8rem;border-top:1px solid #f1f5f9;padding-top:6px;">'
            + '<div>&#x1F321;&#xFE0F; <b>' + d.Harorat + ' \u00b0C</b> &nbsp;&#x1F4A7; <b>' + d.Humidity + '%</b></div>'
            + '<div>&#x26A1; <b>' + d.Kuchlanish + ' V</b> &nbsp;&#x3030;&#xFE0F; <b>' + d.Chastota + ' Hz</b></div>'
            + '<div>&#x1F4A8; <b>' + d.Shamol + ' km/h</b> &nbsp;&#x2699;&#xFE0F; <b>' + d.Quvvat + ' kW</b></div>'
            + '</div><div style="margin-top:8px;">' + slabel + '</div>'
            + '<a href="/sensor/' + d.SensorID + '" style="display:inline-block;margin-top:8px;font-size:0.78rem;color:#2563EB;font-weight:600;text-decoration:none;">Batafsil \u2192</a></div>';

          const opts = { radius: d.Fault===2?9:(d.Fault===1?7:5), color:'rgba(255,255,255,0.85)',
                         fillColor:col, fillOpacity:0.9, weight:1.5, _fault:d.Fault };
          clusterLayer.addLayer(L.circleMarker([d.Latitude, d.Longitude], opts).bindPopup(popup));
          plainLayer.addLayer(L.circleMarker([d.Latitude, d.Longitude], opts).bindPopup(popup));
        });

        if (clusteringEnabled) clusterLayer.addTo(leafletMap);
        else plainLayer.addTo(leafletMap);

        drawDistrictPolygons(district);

        if (district && DISTRICT_BOUNDS[district]) {
          const c = DISTRICT_BOUNDS[district];
          const lats = c.map(x=>x[0]), lons = c.map(x=>x[1]);
          leafletMap.fitBounds([[Math.min(...lats),Math.min(...lons)],[Math.max(...lats),Math.max(...lons)]], {padding:[30,30]});
        }
      } catch(e) {
        console.error('Map error:', e);
        document.getElementById('map-loading').innerHTML =
          '<div class="alert alert-danger m-3"><i class="fas fa-exclamation-circle me-2"></i>Xarita yuklanmadi</div>';
      }
    }

    loadMap();
    setInterval(loadMap, 30000);
    document.getElementById('district-select').addEventListener('change', loadMap);
  </script>
</body>
</html>"""

new_content = head + new_tail
with open(MAP_FILE, 'w', encoding='utf-8') as f:
    f.write(new_content)
print('OK - map.html updated, total lines:', new_content.count('\n') + 1)
