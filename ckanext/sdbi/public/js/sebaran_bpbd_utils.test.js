'use strict';
require('./sebaran_bpbd_utils.js');
var U = globalThis.SebaranBpbdUtils;
var assert = require('assert');

assert.strictEqual(U.escapeHtml('<b>&"\''), '&lt;b&gt;&amp;&quot;&#39;');
assert.strictEqual(U.escapeHtml(null), '');

var features = [
  {
    properties: {
      nama_instansi: 'BPBD DKI Jakarta',
      alamat: 'Monas',
      lat: -6.17,
      lng: 106.82
    },
    geometry: { type: 'Point', coordinates: [106.82, -6.17] }
  },
  {
    properties: {
      nama_instansi: 'BPBD Kabupaten Bogor',
      alamat: 'Cibinong',
      lat: -6.48,
      lng: 106.85
    },
    geometry: { type: 'Point', coordinates: [106.85, -6.48] }
  }
];
assert.strictEqual(U.filterBpbdFeatures(features, 'jakarta').length, 1);
assert.strictEqual(U.filterBpbdFeatures(features, 'cibinong').length, 1);
assert.strictEqual(U.filterBpbdFeatures(features, '').length, 0);
assert.strictEqual(U.filterBpbdFeatures(features, 'bpbd', 1).length, 1);

var html = U.buildPopupHtml({
  nama_instansi: 'BPBD <script>',
  tingkat: 'provinsi',
  kode_wilayah: '31',
  alamat: 'Jl. A',
  telepon: '021',
  email: 'a@b.c',
  jumlah_sdm: 5,
  catatan_sdm: 'TRC',
  maps_url: 'https://www.google.com/maps?q=-6,106',
  lat: -6,
  lng: 106
});
assert.ok(html.indexOf('<script>') === -1);
assert.ok(html.indexOf('BPBD &lt;script&gt;') !== -1);
assert.ok(html.indexOf('tel:021') !== -1);
assert.ok(html.indexOf('mailto:a@b.c') !== -1);
assert.ok(html.indexOf('Website:') === -1);
assert.ok(html.indexOf('provinsi') !== -1);
assert.ok(html.indexOf('Petunjuk arah') !== -1);
assert.ok(html.indexOf('destination=-6,106') !== -1);

var htmlWithSite = U.buildPopupHtml({
  nama_instansi: 'BPBD X',
  website: 'www.example.go.id'
});
assert.ok(htmlWithSite.indexOf('Website:') !== -1);
assert.ok(htmlWithSite.indexOf('href="https://www.example.go.id"') !== -1);
assert.strictEqual(U.websiteHref('http://a.id'), 'http://a.id');
assert.strictEqual(U.websiteHref('www.a.id'), 'https://www.a.id');
assert.strictEqual(U.websiteHref('-'), '');

assert.strictEqual(U.buildPopupHtml({ nama_instansi: 'X' }).indexOf('tel:'), -1);

var one = U.bpbdBounds([features[0]]);
assert.strictEqual(one.type, 'Point');
var many = U.bpbdBounds(features);
assert.ok(many.west <= many.east);
assert.strictEqual(U.bpbdBounds([]), null);

console.log('sebaran_bpbd_utils.test.js OK');
