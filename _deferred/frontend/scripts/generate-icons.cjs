#!/usr/bin/env node
/**
 * Icon Generator for NatLangChain Windows Build
 *
 * This script generates placeholder icon files required by Tauri.
 * For production, replace with proper icons using:
 *   npx @aspect-dev/png path/to/source.png --sizes 32,128,256
 *   or use an online ICO converter
 *
 * Run: node scripts/generate-icons.js
 */

const fs = require('fs');
const path = require('path');

const iconsDir = path.join(__dirname, '..', 'src-tauri', 'icons');

// Create a minimal valid PNG (1x1 purple pixel)
function createMinimalPng(size) {
  // PNG header and minimal IHDR/IDAT/IEND chunks
  // This creates a valid but minimal PNG file
  const pngSignature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);

  // For a proper icon, you'd use a library like 'sharp' or 'canvas'
  // This is just a placeholder that satisfies file existence checks

  // IHDR chunk
  const ihdrData = Buffer.alloc(13);
  ihdrData.writeUInt32BE(size, 0);   // width
  ihdrData.writeUInt32BE(size, 4);   // height
  ihdrData.writeUInt8(8, 8);          // bit depth
  ihdrData.writeUInt8(2, 9);          // color type (RGB)
  ihdrData.writeUInt8(0, 10);         // compression
  ihdrData.writeUInt8(0, 11);         // filter
  ihdrData.writeUInt8(0, 12);         // interlace

  const ihdrCrc = crc32(Buffer.concat([Buffer.from('IHDR'), ihdrData]));
  const ihdr = Buffer.concat([
    Buffer.from([0, 0, 0, 13]),  // length
    Buffer.from('IHDR'),
    ihdrData,
    ihdrCrc
  ]);

  // Minimal IDAT with solid purple color
  const rawData = [];
  for (let y = 0; y < size; y++) {
    rawData.push(0); // filter byte
    for (let x = 0; x < size; x++) {
      rawData.push(102, 126, 234); // RGB for #667eea
    }
  }

  // Simple deflate (store mode)
  const rawBuffer = Buffer.from(rawData);
  const deflated = deflateRaw(rawBuffer);

  const idatCrc = crc32(Buffer.concat([Buffer.from('IDAT'), deflated]));
  const idatLen = Buffer.alloc(4);
  idatLen.writeUInt32BE(deflated.length, 0);
  const idat = Buffer.concat([
    idatLen,
    Buffer.from('IDAT'),
    deflated,
    idatCrc
  ]);

  // IEND chunk
  const iendCrc = crc32(Buffer.from('IEND'));
  const iend = Buffer.concat([
    Buffer.from([0, 0, 0, 0]),  // length
    Buffer.from('IEND'),
    iendCrc
  ]);

  return Buffer.concat([pngSignature, ihdr, idat, iend]);
}

// Simple CRC32 implementation
function crc32(data) {
  let crc = 0xFFFFFFFF;
  const table = [];

  for (let i = 0; i < 256; i++) {
    let c = i;
    for (let j = 0; j < 8; j++) {
      c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
    }
    table[i] = c;
  }

  for (let i = 0; i < data.length; i++) {
    crc = table[(crc ^ data[i]) & 0xFF] ^ (crc >>> 8);
  }

  const result = Buffer.alloc(4);
  result.writeUInt32BE((crc ^ 0xFFFFFFFF) >>> 0, 0);
  return result;
}

// Minimal deflate (uncompressed blocks)
function deflateRaw(data) {
  const chunks = [];
  const maxBlock = 65535;

  for (let i = 0; i < data.length; i += maxBlock) {
    const chunk = data.slice(i, Math.min(i + maxBlock, data.length));
    const isLast = (i + maxBlock >= data.length) ? 1 : 0;

    const header = Buffer.alloc(5);
    header.writeUInt8(isLast, 0);
    header.writeUInt16LE(chunk.length, 1);
    header.writeUInt16LE(~chunk.length & 0xFFFF, 3);

    chunks.push(header, chunk);
  }

  // Wrap in zlib format
  const zlibHeader = Buffer.from([0x78, 0x01]); // No compression
  const content = Buffer.concat(chunks);

  // Adler32 checksum
  let a = 1, b = 0;
  for (let i = 0; i < data.length; i++) {
    a = (a + data[i]) % 65521;
    b = (b + a) % 65521;
  }
  const adler = Buffer.alloc(4);
  adler.writeUInt32BE((b << 16) | a, 0);

  return Buffer.concat([zlibHeader, content, adler]);
}

// Create a minimal ICO file
function createIco(sizes) {
  const images = sizes.map(size => ({
    size,
    data: createBmpData(size)
  }));

  // ICO header
  const header = Buffer.alloc(6);
  header.writeUInt16LE(0, 0);              // Reserved
  header.writeUInt16LE(1, 2);              // Type: 1 = ICO
  header.writeUInt16LE(images.length, 4);  // Number of images

  // Directory entries
  let offset = 6 + (images.length * 16);
  const entries = images.map(img => {
    const entry = Buffer.alloc(16);
    entry.writeUInt8(img.size < 256 ? img.size : 0, 0);   // Width
    entry.writeUInt8(img.size < 256 ? img.size : 0, 1);   // Height
    entry.writeUInt8(0, 2);                                 // Colors
    entry.writeUInt8(0, 3);                                 // Reserved
    entry.writeUInt16LE(1, 4);                              // Color planes
    entry.writeUInt16LE(32, 6);                             // Bits per pixel
    entry.writeUInt32LE(img.data.length, 8);               // Size
    entry.writeUInt32LE(offset, 12);                        // Offset
    offset += img.data.length;
    return entry;
  });

  return Buffer.concat([header, ...entries, ...images.map(i => i.data)]);
}

// Create BMP data for ICO
function createBmpData(size) {
  const rowSize = size * 4;
  const pixelData = Buffer.alloc(size * rowSize);

  // Fill with purple color (BGRA format)
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const offset = (size - 1 - y) * rowSize + x * 4;
      pixelData[offset] = 234;      // B
      pixelData[offset + 1] = 126;  // G
      pixelData[offset + 2] = 102;  // R
      pixelData[offset + 3] = 255;  // A
    }
  }

  // BMP info header (BITMAPINFOHEADER)
  const header = Buffer.alloc(40);
  header.writeUInt32LE(40, 0);           // Header size
  header.writeInt32LE(size, 4);          // Width
  header.writeInt32LE(size * 2, 8);      // Height (doubled for ICO)
  header.writeUInt16LE(1, 12);           // Planes
  header.writeUInt16LE(32, 14);          // Bits per pixel
  header.writeUInt32LE(0, 16);           // Compression
  header.writeUInt32LE(pixelData.length, 20);  // Image size

  return Buffer.concat([header, pixelData]);
}

// Main
console.log('Generating placeholder icons for NatLangChain...');
console.log('');

// Ensure icons directory exists
if (!fs.existsSync(iconsDir)) {
  fs.mkdirSync(iconsDir, { recursive: true });
}

// Generate PNGs
const pngSizes = [
  { name: '32x32.png', size: 32 },
  { name: '128x128.png', size: 128 },
  { name: '128x128@2x.png', size: 256 }
];

for (const { name, size } of pngSizes) {
  const filepath = path.join(iconsDir, name);
  try {
    fs.writeFileSync(filepath, createMinimalPng(size));
    console.log(`  Created: ${name}`);
  } catch (err) {
    console.log(`  Warning: Could not create ${name}: ${err.message}`);
  }
}

// Generate ICO (Windows icon)
const icoPath = path.join(iconsDir, 'icon.ico');
try {
  fs.writeFileSync(icoPath, createIco([16, 32, 48, 256]));
  console.log('  Created: icon.ico');
} catch (err) {
  console.log(`  Warning: Could not create icon.ico: ${err.message}`);
}

// Create empty ICNS placeholder (macOS)
const icnsPath = path.join(iconsDir, 'icon.icns');
try {
  // Minimal valid ICNS file
  const icnsHeader = Buffer.from('icns');
  const size = Buffer.alloc(4);
  size.writeUInt32BE(8, 0);
  fs.writeFileSync(icnsPath, Buffer.concat([icnsHeader, size]));
  console.log('  Created: icon.icns (placeholder)');
} catch (err) {
  console.log(`  Warning: Could not create icon.icns: ${err.message}`);
}

console.log('');
console.log('Done! Icons generated at: src-tauri/icons/');
console.log('');
console.log('For production, generate proper icons using:');
console.log('  npx tauri icon path/to/your/1024x1024-icon.png');
