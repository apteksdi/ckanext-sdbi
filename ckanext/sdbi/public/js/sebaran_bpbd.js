(function () {
  var mapEl = document.getElementById('sebaran-bpbd-map');
  if (!mapEl || typeof maplibregl === 'undefined') {
    return;
  }

  var U = globalThis.SebaranBpbdUtils || null;

  var root = document.querySelector('.sebaran-bpbd');
  var map;
  var bpbdFeatures = [];
  var bpbdIndex = null;
  var activePopup = null;
  var highlightTimer = null;
  var BPBD_LAYER_IDS = ['bpbd-clusters', 'bpbd-cluster-count', 'bpbd-points'];

  function fallbackEscapeHtml(value) {
    if (value == null || value === '') {
      return '';
    }
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function popupHtmlFallback(props) {
    props = props || {};
    var maps = props.maps_url || ('https://www.google.com/maps?q=' + props.lat + ',' + props.lng);
    return (
      '<div class="sebaran-bpbd-popup">' +
      '<h3>' + fallbackEscapeHtml(props.nama_instansi || 'BPBD') + '</h3>' +
      '<p>' + fallbackEscapeHtml(props.alamat || '-') + '</p>' +
      '<p><strong>SDM:</strong> ' + fallbackEscapeHtml(props.jumlah_sdm != null ? props.jumlah_sdm : '-') + '</p>' +
      '<p>' + fallbackEscapeHtml(props.catatan_sdm || '') + '</p>' +
      '<p><a href="' + fallbackEscapeHtml(maps) + '" target="_blank" rel="noopener">Buka di Google Maps</a></p>' +
      '</div>'
    );
  }

  function buildPopup(props) {
    return U ? U.buildPopupHtml(props) : popupHtmlFallback(props);
  }

  function applyHeaderOffset() {
    var bar = document.querySelector('.sebaran-bpbd__bar');
    var bottom = 0;
    if (bar) {
      bottom = bar.getBoundingClientRect().bottom;
    }
    if (bottom > 0 && root) {
      root.style.setProperty('--sb-header-offset', Math.ceil(bottom) + 'px');
    }
  }

  function syncHeaderOffset() {
    applyHeaderOffset();
    if (map) {
      map.resize();
    }
  }

  function setExploreStatus(message) {
    var el = document.getElementById('sebaran-bpbd-search-status');
    if (el) {
      el.textContent = message || '';
    }
  }

  function enableExploreControls() {
    var search = document.getElementById('sebaran-bpbd-search');
    var fit = document.getElementById('sebaran-bpbd-fit-all');
    if (search) {
      search.disabled = false;
    }
    if (fit) {
      fit.disabled = !bpbdFeatures.length;
    }
    if (!bpbdFeatures.length) {
      setExploreStatus('Belum ada titik terpetakan.');
    } else {
      setExploreStatus('');
    }
  }

  function clearSearchResults() {
    var list = document.getElementById('sebaran-bpbd-search-results');
    if (!list) {
      return;
    }
    list.innerHTML = '';
    list.hidden = true;
  }

  function openFeaturePopup(feature) {
    if (!feature || !map) {
      return;
    }
    var coords = feature.geometry.coordinates;
    var props = feature.properties || {};
    if (activePopup) {
      activePopup.remove();
    }
    activePopup = new maplibregl.Popup({ closeButton: true, maxWidth: '300px' })
      .setLngLat(coords)
      .setHTML(buildPopup(props))
      .addTo(map);
    map.flyTo({ center: coords, zoom: Math.max(map.getZoom(), 9.5) });
    try {
      if (map.getLayer('bpbd-points')) {
        map.setPaintProperty('bpbd-points', 'circle-stroke-width', 3);
        if (highlightTimer) {
          window.clearTimeout(highlightTimer);
        }
        highlightTimer = window.setTimeout(function () {
          if (map.getLayer('bpbd-points')) {
            map.setPaintProperty('bpbd-points', 'circle-stroke-width', 2);
          }
        }, 2000);
      }
    } catch (e) {
      // ignore paint highlight failures
    }
  }

  function fitAllBpbd() {
    if (!U) {
      setExploreStatus('Fit tidak tersedia.');
      return;
    }
    var bounds = U.bpbdBounds(visibleBpbdFeatures());
    if (!bounds) {
      setExploreStatus('Belum ada titik terpetakan untuk filter aktif.');
      return;
    }
    var bar = document.querySelector('.sebaran-bpbd__bar');
    var topPad = bar ? Math.ceil(bar.getBoundingClientRect().height) + 16 : 72;
    if (bounds.type === 'Point') {
      map.flyTo({ center: bounds.coordinates, zoom: 10 });
      return;
    }
    map.fitBounds(
      [[bounds.west, bounds.south], [bounds.east, bounds.north]],
      { padding: { top: topPad, bottom: 48, left: 40, right: 40 }, maxZoom: 8 }
    );
  }

  function bindExploreControls() {
    if (!U) {
      return;
    }
    var search = document.getElementById('sebaran-bpbd-search');
    var list = document.getElementById('sebaran-bpbd-search-results');
    var fit = document.getElementById('sebaran-bpbd-fit-all');
    if (fit) {
      fit.addEventListener('click', fitAllBpbd);
    }
    if (!search || !list) {
      return;
    }
    search.addEventListener('input', function () {
      var matches = U.filterBpbdFeatures(bpbdFeatures, search.value, 20);
      list.innerHTML = '';
      if (!String(search.value || '').trim()) {
        clearSearchResults();
        setExploreStatus('');
        return;
      }
      if (!matches.length) {
        list.hidden = true;
        setExploreStatus('Tidak ditemukan');
        return;
      }
      setExploreStatus(matches.length + ' hasil');
      matches.forEach(function (feature) {
        var p = feature.properties || {};
        var li = document.createElement('li');
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.setAttribute('role', 'option');
        btn.innerHTML = '<strong></strong><span></span>';
        btn.querySelector('strong').textContent = p.nama_instansi || 'BPBD';
        btn.querySelector('span').textContent = p.alamat || '';
        btn.addEventListener('click', function () {
          openFeaturePopup(feature);
          clearSearchResults();
          search.value = p.nama_instansi || '';
          setExploreStatus('');
        });
        li.appendChild(btn);
        list.appendChild(li);
      });
      list.hidden = false;
    });
  }

  applyHeaderOffset();
  map = new maplibregl.Map({
    container: 'sebaran-bpbd-map',
    style: 'https://tiles.openfreemap.org/styles/bright',
    center: [118.0, -2.5],
    zoom: 5.0,
    attributionControl: false
  });
  map.addControl(new maplibregl.NavigationControl({ visualizePitch: false }), 'top-right');
  map.addControl(new maplibregl.ScaleControl({ maxWidth: 120 }), 'bottom-right');

  function syncOpenGmapsLink() {
    var link = document.getElementById('sebaran-bpbd-open-gmaps');
    if (!link || !map) {
      return;
    }
    var c = map.getCenter();
    var z = Math.max(1, Math.round(map.getZoom()));
    link.href = 'https://www.google.com/maps/@' + c.lat.toFixed(6) + ',' + c.lng.toFixed(6) + ',' + z + 'z';
  }
  map.on('moveend', syncOpenGmapsLink);
  syncOpenGmapsLink();
  syncHeaderOffset();
  window.addEventListener('resize', syncHeaderOffset);

  function applyBpbdData(geojson) {
    bpbdFeatures = (geojson && geojson.features) || [];
    var count = bpbdFeatures.length;
    var strong = document.querySelector('.sebaran-bpbd__count strong');
    if (strong) {
      strong.textContent = count;
    }
    enableExploreControls();
    syncBpbdPointFilter();
  }

  function visibleBpbdFeatures() {
    var showProv = !!(document.getElementById('layer-provinsi') || {}).checked;
    var showKab = !!(document.getElementById('layer-kabupaten') || {}).checked;
    var showPoints = !!(document.getElementById('layer-bpbd') || {}).checked;
    if (!showPoints || (!showProv && !showKab)) {
      return [];
    }
    return bpbdFeatures.filter(function (feature) {
      var tingkat = ((feature.properties || {}).tingkat || '').toLowerCase();
      if (tingkat === 'provinsi') {
        return showProv;
      }
      if (tingkat === 'kabupaten') {
        return showKab;
      }
      return false;
    });
  }

  function filteredBpbdGeojson() {
    return {
      type: 'FeatureCollection',
      features: visibleBpbdFeatures()
    };
  }

  function bindImportDialog() {
    var dialog = document.getElementById('sebaran-bpbd-import');
    var openBtn = document.querySelector('.sebaran-bpbd__upload-open');
    if (!dialog || !openBtn || typeof dialog.showModal !== 'function') {
      return;
    }
    var form = dialog.querySelector('.sebaran-bpbd__dialog-form');
    var fileInput = form.querySelector('input[type="file"]');
    var fileLabel = dialog.querySelector('.sebaran-bpbd__drop-file');
    var drop = dialog.querySelector('.sebaran-bpbd__drop');
    var statusEl = dialog.querySelector('.sebaran-bpbd__dialog-status');
    var submitBtn = dialog.querySelector('.sebaran-bpbd__dialog-submit');
    var closeBtns = dialog.querySelectorAll('.sebaran-bpbd__dialog-close, .sebaran-bpbd__dialog-cancel');

    function setStatus(message, kind) {
      statusEl.textContent = message || '';
      statusEl.classList.remove('is-error', 'is-ok');
      if (kind) {
        statusEl.classList.add(kind);
      }
    }

    function resetForm() {
      form.reset();
      fileLabel.textContent = 'Belum ada berkas dipilih';
      submitBtn.disabled = true;
      submitBtn.textContent = 'Impor ke peta';
      setStatus('');
      drop.classList.remove('is-active');
    }

    function closeDialog() {
      if (dialog.open) {
        dialog.close();
      }
    }

    openBtn.addEventListener('click', function () {
      resetForm();
      dialog.showModal();
    });
    closeBtns.forEach(function (btn) {
      btn.addEventListener('click', closeDialog);
    });
    dialog.addEventListener('click', function (event) {
      if (event.target === dialog) {
        closeDialog();
      }
    });
    fileInput.addEventListener('change', function () {
      var file = fileInput.files && fileInput.files[0];
      fileLabel.textContent = file ? file.name : 'Belum ada berkas dipilih';
      submitBtn.disabled = !file;
      setStatus('');
    });
    ['dragenter', 'dragover'].forEach(function (type) {
      drop.addEventListener(type, function (event) {
        event.preventDefault();
        drop.classList.add('is-active');
      });
    });
    ['dragleave', 'drop'].forEach(function (type) {
      drop.addEventListener(type, function (event) {
        event.preventDefault();
        drop.classList.remove('is-active');
      });
    });
    drop.addEventListener('drop', function (event) {
      var files = event.dataTransfer && event.dataTransfer.files;
      if (!files || !files.length) {
        return;
      }
      fileInput.files = files;
      fileInput.dispatchEvent(new Event('change', { bubbles: true }));
    });
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      if (!fileInput.files || !fileInput.files[0]) {
        setStatus('Pilih berkas CSV terlebih dahulu.', 'is-error');
        return;
      }
      submitBtn.disabled = true;
      submitBtn.textContent = 'Mengimpor…';
      setStatus('');
      fetch(form.action, {
        method: 'POST',
        body: new FormData(form),
        credentials: 'same-origin'
      })
        .then(function (res) {
          return res.json().then(function (body) {
            return { ok: res.ok, status: res.status, body: body };
          }).catch(function () {
            throw new Error(res.status === 403
              ? 'Sesi berakhir. Masuk lagi sebagai sysadmin.'
              : 'Impor gagal. Periksa berkas CSV lalu coba lagi.');
          });
        })
        .then(function (result) {
          if (!result.ok || !result.body.success) {
            throw new Error(result.body.error || 'Impor gagal. Periksa berkas CSV lalu coba lagi.');
          }
          setStatus(
            result.body.mapped + ' lokasi terpetakan dari ' + result.body.imported + ' baris.',
            'is-ok'
          );
          return fetch('/sebaran-bpbd/data.geojson').then(function (res) {
            return res.json();
          });
        })
        .then(function (geojson) {
          if (geojson) {
            applyBpbdData(geojson);
          }
          submitBtn.textContent = 'Impor ke peta';
          window.setTimeout(closeDialog, 900);
        })
        .catch(function (err) {
          setStatus(err.message || 'Impor gagal.', 'is-error');
          submitBtn.disabled = false;
          submitBtn.textContent = 'Impor ke peta';
        });
    });
  }
  bindImportDialog();
  bindExploreControls();

  function setVisibility(layerId, visible) {
    if (map.getLayer(layerId)) {
      map.setLayoutProperty(layerId, 'visibility', visible ? 'visible' : 'none');
    }
  }

  function rebuildBpbdIndex() {
    if (typeof Supercluster === 'undefined') {
      bpbdIndex = null;
      return;
    }
    bpbdIndex = new Supercluster({
      radius: 60,
      maxZoom: 14
    });
    bpbdIndex.load(visibleBpbdFeatures());
  }

  function updateBpbdClusters() {
    if (!map || !map.getSource('bpbd')) {
      return;
    }
    if (!bpbdIndex) {
      map.getSource('bpbd').setData(filteredBpbdGeojson());
      return;
    }
    var bounds = map.getBounds();
    var bbox = [
      bounds.getWest(),
      bounds.getSouth(),
      bounds.getEast(),
      bounds.getNorth()
    ];
    var zoom = Math.max(0, Math.floor(map.getZoom()));
    map.getSource('bpbd').setData({
      type: 'FeatureCollection',
      features: bpbdIndex.getClusters(bbox, zoom)
    });
  }

  function setBpbdLayersVisible(visible) {
    var value = visible ? 'visible' : 'none';
    BPBD_LAYER_IDS.forEach(function (id) {
      if (map.getLayer(id)) {
        map.setLayoutProperty(id, 'visibility', value);
      }
    });
  }

  function syncBpbdPointFilter() {
    if (!map || !map.getSource('bpbd')) {
      return;
    }
    rebuildBpbdIndex();
    updateBpbdClusters();
    var showPoints = !!(document.getElementById('layer-bpbd') || {}).checked;
    setBpbdLayersVisible(showPoints);
  }

  function beforePoints() {
    if (map.getLayer('bpbd-clusters')) {
      return 'bpbd-clusters';
    }
    if (map.getLayer('bpbd-points')) {
      return 'bpbd-points';
    }
    return undefined;
  }

  var bpbdEventsBound = false;

  function addBpbdLayers() {
    rebuildBpbdIndex();

    var empty = { type: 'FeatureCollection', features: [] };
    if (!map.getSource('bpbd')) {
      map.addSource('bpbd', {
        type: 'geojson',
        data: empty
      });
    }

    if (!map.getLayer('bpbd-clusters')) {
      map.addLayer({
        id: 'bpbd-clusters',
        type: 'circle',
        source: 'bpbd',
        filter: ['has', 'point_count'],
        paint: {
          'circle-color': '#d93025',
          'circle-radius': [
            'step',
            ['get', 'point_count'],
            16,
            10, 20,
            50, 26,
            100, 32
          ],
          'circle-stroke-width': 2,
          'circle-stroke-color': '#ffffff'
        }
      });
    }

    if (!map.getLayer('bpbd-cluster-count')) {
      map.addLayer({
        id: 'bpbd-cluster-count',
        type: 'symbol',
        source: 'bpbd',
        filter: ['has', 'point_count'],
        layout: {
          'text-field': '{point_count_abbreviated}',
          'text-size': 12,
          'text-font': ['Noto Sans Bold'],
          'text-allow-overlap': true
        },
        paint: {
          'text-color': '#ffffff'
        }
      });
    }

    if (!map.getLayer('bpbd-points')) {
      map.addLayer({
        id: 'bpbd-points',
        type: 'circle',
        source: 'bpbd',
        filter: ['!', ['has', 'point_count']],
        paint: {
          'circle-radius': [
            'interpolate', ['linear'], ['zoom'],
            4, 3,
            8, 5,
            12, 8
          ],
          'circle-color': '#d93025',
          'circle-stroke-width': 2,
          'circle-stroke-color': '#ffffff'
        }
      });
    }

    syncBpbdPointFilter();

    if (bpbdEventsBound) {
      return;
    }
    bpbdEventsBound = true;

    map.on('moveend', updateBpbdClusters);
    map.on('zoomend', updateBpbdClusters);

    map.on('click', 'bpbd-clusters', function (e) {
      var feature = e.features && e.features[0];
      if (!feature || !bpbdIndex) {
        return;
      }
      var clusterId = feature.properties.cluster_id;
      var expansionZoom = bpbdIndex.getClusterExpansionZoom(clusterId);
      map.flyTo({
        center: feature.geometry.coordinates,
        zoom: expansionZoom
      });
    });

    map.on('click', 'bpbd-points', function (e) {
      openFeaturePopup(e.features[0]);
    });

    ['bpbd-clusters', 'bpbd-points'].forEach(function (layerId) {
      map.on('mouseenter', layerId, function () {
        map.getCanvas().style.cursor = 'pointer';
      });
      map.on('mouseleave', layerId, function () {
        map.getCanvas().style.cursor = '';
      });
    });
  }

  map.on('load', function () {
    map.resize();

    fetch('/data/boundaries/provinsi.geojson')
      .then(function (res) { return res.json(); })
      .then(function (geojson) {
        map.addSource('provinsi', { type: 'geojson', data: geojson });
        map.addLayer({
          id: 'provinsi-fill',
          type: 'fill',
          source: 'provinsi',
          paint: {
            'fill-color': '#1a73e8',
            'fill-opacity': 0.10
          }
        }, beforePoints());
        map.addLayer({
          id: 'provinsi-line',
          type: 'line',
          source: 'provinsi',
          paint: {
            'line-color': '#1a73e8',
            'line-width': 1.2
          }
        }, beforePoints());
      })
      .catch(function () {});

    fetch('/data/boundaries/kabupaten.geojson')
      .then(function (res) { return res.ok ? res.json() : null; })
      .then(function (geojson) {
        if (geojson && geojson.features && geojson.features.length) {
          map.addSource('kabupaten', { type: 'geojson', data: geojson });
          map.addLayer({
            id: 'kabupaten-fill',
            type: 'fill',
            source: 'kabupaten',
            paint: { 'fill-color': '#e37400', 'fill-opacity': 0.06 }
          }, beforePoints());
          map.addLayer({
            id: 'kabupaten-line',
            type: 'line',
            source: 'kabupaten',
            paint: { 'line-color': '#e37400', 'line-width': 0.6 }
          }, beforePoints());
          return;
        }
        var sources = map.getStyle().sources || {};
        var vectorId = null;
        Object.keys(sources).forEach(function (id) {
          if (!vectorId && sources[id].type === 'vector') {
            vectorId = id;
          }
        });
        if (!vectorId) {
          return;
        }
        map.addLayer({
          id: 'kabupaten-line',
          type: 'line',
          source: vectorId,
          'source-layer': 'boundary',
          filter: ['all', ['==', ['get', 'admin_level'], 6]],
          paint: { 'line-color': '#e37400', 'line-width': 0.7 }
        }, beforePoints());
      })
      .catch(function () {});

    fetch('/sebaran-bpbd/data.geojson')
      .then(function (res) { return res.json(); })
      .then(function (geojson) {
        applyBpbdData(geojson);
        addBpbdLayers();
      })
      .catch(function () {});
  });

  function bindToggle(checkboxId, layerIds) {
    var el = document.getElementById(checkboxId);
    if (!el) {
      return;
    }
    el.addEventListener('change', function () {
      layerIds.forEach(function (id) {
        setVisibility(id, el.checked);
      });
      if (checkboxId === 'layer-provinsi' || checkboxId === 'layer-kabupaten' || checkboxId === 'layer-bpbd') {
        syncBpbdPointFilter();
      }
    });
  }

  bindToggle('layer-provinsi', ['provinsi-fill', 'provinsi-line']);
  bindToggle('layer-kabupaten', ['kabupaten-fill', 'kabupaten-line']);
  bindToggle('layer-bpbd', []);
})();
