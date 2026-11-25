(function (root) {
  'use strict';

  function escapeHtml(value) {
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

  function websiteHref(value) {
    var raw = String(value || '').trim();
    if (!raw || raw === '-' || raw === '–') {
      return '';
    }
    if (/^https?:\/\//i.test(raw)) {
      return raw;
    }
    return 'https://' + raw;
  }

  function filterBpbdFeatures(features, query, limit) {
    var q = String(query || '').trim().toLowerCase();
    if (!q || !features || !features.length) {
      return [];
    }
    var max = limit == null ? 20 : limit;
    var out = [];
    for (var i = 0; i < features.length && out.length < max; i++) {
      var p = (features[i] && features[i].properties) || {};
      var name = String(p.nama_instansi || '').toLowerCase();
      var addr = String(p.alamat || '').toLowerCase();
      if (name.indexOf(q) !== -1 || addr.indexOf(q) !== -1) {
        out.push(features[i]);
      }
    }
    return out;
  }

  function buildPopupHtml(props) {
    props = props || {};
    var lat = props.lat;
    var lng = props.lng;
    var maps = props.maps_url || (
      lat != null && lng != null
        ? 'https://www.google.com/maps?q=' + lat + ',' + lng
        : ''
    );
    var directions = (
      lat != null && lng != null
        ? 'https://www.google.com/maps/dir/?api=1&destination=' + lat + ',' + lng
        : ''
    );
    var parts = ['<div class="sebaran-bpbd-popup">'];
    parts.push('<h3>' + escapeHtml(props.nama_instansi || 'BPBD') + '</h3>');
    var meta = [];
    if (props.tingkat) {
      meta.push(escapeHtml(props.tingkat));
    }
    if (props.kode_wilayah) {
      meta.push('kode ' + escapeHtml(props.kode_wilayah));
    }
    if (meta.length) {
      parts.push('<p class="sebaran-bpbd-popup__meta">' + meta.join(' · ') + '</p>');
    }
    if (props.alamat) {
      parts.push('<p>' + escapeHtml(props.alamat) + '</p>');
    }
    if (props.telepon) {
      parts.push(
        '<p><strong>Telepon:</strong> <a href="tel:' +
          escapeHtml(props.telepon) +
          '">' +
          escapeHtml(props.telepon) +
          '</a></p>'
      );
    }
    if (props.email) {
      parts.push(
        '<p><strong>Email:</strong> <a href="mailto:' +
          escapeHtml(props.email) +
          '">' +
          escapeHtml(props.email) +
          '</a></p>'
      );
    }
    var siteHref = websiteHref(props.website);
    if (siteHref) {
      parts.push(
        '<p><strong>Website:</strong> <a href="' +
          escapeHtml(siteHref) +
          '" target="_blank" rel="noopener">' +
          escapeHtml(String(props.website).trim()) +
          '</a></p>'
      );
    }
    if (props.jumlah_sdm != null && props.jumlah_sdm !== '') {
      parts.push('<p><strong>SDM:</strong> ' + escapeHtml(props.jumlah_sdm) + '</p>');
    }
    if (props.catatan_sdm) {
      parts.push('<p>' + escapeHtml(props.catatan_sdm) + '</p>');
    }
    if (maps || directions) {
      parts.push('<div class="sebaran-bpbd-popup__actions">');
      if (maps) {
        parts.push(
          '<a class="sebaran-bpbd-popup__btn" href="' +
            escapeHtml(maps) +
            '" target="_blank" rel="noopener">Buka di Google Maps</a>'
        );
      }
      if (directions) {
        parts.push(
          '<a class="sebaran-bpbd-popup__btn sebaran-bpbd-popup__btn--ghost" href="' +
            escapeHtml(directions) +
            '" target="_blank" rel="noopener">Petunjuk arah</a>'
        );
      }
      parts.push('</div>');
    }
    parts.push('</div>');
    return parts.join('');
  }

  function bpbdBounds(features) {
    if (!features || !features.length) {
      return null;
    }
    if (features.length === 1) {
      var g = features[0].geometry;
      if (!g || g.type !== 'Point') {
        return null;
      }
      return { type: 'Point', coordinates: g.coordinates };
    }
    var west = Infinity;
    var south = Infinity;
    var east = -Infinity;
    var north = -Infinity;
    for (var i = 0; i < features.length; i++) {
      var geom = features[i].geometry;
      if (!geom || geom.type !== 'Point') {
        continue;
      }
      var lng = geom.coordinates[0];
      var lat = geom.coordinates[1];
      if (lng < west) {
        west = lng;
      }
      if (lat < south) {
        south = lat;
      }
      if (lng > east) {
        east = lng;
      }
      if (lat > north) {
        north = lat;
      }
    }
    if (!isFinite(west)) {
      return null;
    }
    return {
      type: 'LngLatBoundsLike',
      west: west,
      south: south,
      east: east,
      north: north
    };
  }

  root.SebaranBpbdUtils = {
    escapeHtml: escapeHtml,
    websiteHref: websiteHref,
    filterBpbdFeatures: filterBpbdFeatures,
    buildPopupHtml: buildPopupHtml,
    bpbdBounds: bpbdBounds
  };
})(typeof globalThis !== 'undefined' ? globalThis : this);
