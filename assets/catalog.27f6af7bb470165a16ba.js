'use strict';
// Data is generated solely from products/*/product.json. No fetch: works with file://.
const items = (window.CATALOG || []).map(product => ({
  ...product,
  tags: [...new Set(product.tags || [])],
  images: product.images || [],
  characteristics: Object.fromEntries(Object.entries(product.characteristics || {}).map(([key,value]) => [key,value.trim()])),
  size: (product.size || product.height || '').trim(),
  description: (product.description || '').trim(),
  tag: (product.tag || '').trim()
}));
