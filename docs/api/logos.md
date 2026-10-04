# Local airline-logo descriptor and binary contract

M1 draft **0.1**, 2026-10-03; runtime implementation belongs to M6.
No airline artwork collection, approved asset manifest, bitmap endpoint or ESP32
bitmap cache is implemented by this document. VRS airline records currently
provide names/codes; they do not contain logo images.

## 1. Identity and manifest join

First resolve `operator.id` through applicable dated operator evidence or a
recognized unambiguous airline reference. Then perform an exact approved-manifest
join on that identity, such as `airline:BAW`. Do not join on registered owner,
registration, aircraft manufacturer/model, ambiguous IATA text, or airport name.
[Enrichment joins](enrichment-joins.md) defines that boundary in detail.

The manifest maps the stable operator key to immutable converted bytes. The
identity and hash have different lifetimes: one airline can gain a new asset hash
after corrected artwork/conversion, while a given hash always means the same bytes.
Only a validated approved row can produce a non-null descriptor. Unknown operator,
missing approval, missing/corrupt conversion or conflicting mapping produces
`logo=null`, with useful telemetry retained.

## 2. JSON descriptor

The complete descriptor is embedded under a flight's `logo` or is null. The
[descriptor schema](logo-v1.schema.json) is referenced by the flight schema.

| Field | Type / exact rule | Meaning |
| --- | --- | --- |
| `operator_id` | Namespaced `airline:{canonical_code}`, ≤16 chars | Must equal that card's currently resolved `operator.id`. |
| `source_id` | Response-local source ID, ≤8 chars | Join to the approved logo-manifest generation in `reference_sources`. |
| `path` | `/assets/logos/{64-lowercase-hex-sha256}.rgb565` | Relative path on the configured Pi's same host/port. No query, traversal or external URL. |
| `sha256` | Exactly 64 lowercase hex characters | SHA-256 of the raw 1,152 pixel bytes; must equal the hash in `path`. |
| `width` | Exactly 24 | Pixel width. |
| `height` | Exactly 24 | Pixel height. |
| `format` | Exactly `rgb565` | Binary pixel format, not PNG/JPEG/SVG. |
| `byte_order` | Exactly `big_endian` | Most significant byte of each 16-bit pixel first. |
| `size_bytes` | Exactly 1,152 | 24 × 24 × 2. |

The descriptor exposes what the client needs to safely render/copy the artifact;
license URLs, source-image dimensions, approval evidence and conversion tooling
remain in the Pi manifest/meta. Byte validation does not itself establish reuse
permission; the asset has already passed the maintenance approval boundary.

## 3. Asset HTTP contract

```text
GET /assets/logos/<sha256>.rgb565 HTTP/1.1
Accept: application/octet-stream
Accept-Encoding: identity
```

| Response | Headers/body | ESP32 behavior |
| --- | --- | --- |
| HTTP 200 | `Content-Type: application/octet-stream`, `Content-Length: 1152`, exactly 1,152 identity-encoded bytes | Validate shape/operator/path/hash/length, then activate/cache. |
| HTTP 304, if conditional GET is implemented | No body; matching strong ETag | Use only a previously validated matching cache entry. A 304 without those bytes is not success. |
| HTTP 404 | Asset absent | Badge fallback; bounded retry, no internet lookup. |
| HTTP 4xx/5xx/timeout | Asset request failure | Keep telemetry; use badge or an already validated matching hash. |
| Redirect/unexpected encoding/length/hash | Invalid asset contract | Reject asset; never follow to an external origin or reinterpret compressed bytes. |

For successful immutable assets, use strong `ETag: "{sha256}"` and
`Cache-Control: public, max-age=31536000, immutable`. Conditional requests are
optional; first firmware can avoid the request entirely when its hash cache hits.
No arbitrary filesystem/image URL is accepted as a request parameter. The server
resolves only the exact bounded hash filename into its approved artifact store.

Initial asset request timeout is two seconds. A stalled asset operation cannot
block the rendering/flight expiry loop. Flight polling/state processing has
priority; never fetch artwork on every render frame or repeatedly for each
candidate when the content hash is already cached.

## 4. Exact pixel layout

Rows are top to bottom; pixels within a row are left to right. There is no header,
palette, row padding, transparency channel, compression or footer.

```text
pixel_index = y * 24 + x             (x and y are 0..23)
byte_offset = pixel_index * 2
pixel_word = (bytes[offset] << 8) | bytes[offset + 1]

red5   = (pixel_word >> 11) & 0x1f
green6 = (pixel_word >> 5)  & 0x3f
blue5  = pixel_word        & 0x1f
```

For maintenance conversion from an 8-bit RGB result:

```text
rgb565 = ((red8 >> 3) << 11) | ((green8 >> 2) << 5) | (blue8 >> 3)
output first  = (rgb565 >> 8) & 0xff
output second = rgb565 & 0xff
```

| Pixel | 16-bit word | Wire bytes |
| --- | --- | --- |
| Black | `0x0000` | `00 00` |
| Red | `0xF800` | `F8 00` |
| Green | `0x07E0` | `07 E0` |
| Blue | `0x001F` | `00 1F` |
| White | `0xFFFF` | `FF FF` |

Composite source transparency onto black during maintenance; it is not an ESP32
alpha operation. Maintain aspect ratio, fit into the 24×24 square, and center with
black padding. Record resize filter/conversion version in the manifest so an
updated recipe yields a new hash. Pixel values are RGB; physical LED color order
and matrix wiring are separate renderer/hardware configuration, not asset encoding.

## 5. Maintenance manifest requirements

A manifest row must retain at least:

| Group | Required information |
| --- | --- |
| Identity | Exact operator ID; known airline code identity/source; intentional aliases/version scope. |
| Source artwork | Source URI and revision/retrieval time; original checksum, media type, original dimensions/size. |
| Reuse/approval | Artifact-specific terms/license label/URI, attribution/credits, explicit approved state and evidence of review. |
| Conversion | Converter/recipe version, dimensions, fit/padding/transparency policy, RGB565 byte order, output size. |
| Output | Raw bytes SHA-256 and relative hash path, converted-file availability/validation. |
| Generation | Validated activation generation, counts/checksums and retained prior-generation relationship. |

VRS CC0 covers its published tables, not unrelated artwork. An API software
license or an airline-name mapping is not an image license. Keep artwork terms
with the actual imported artifact, including any required attribution outside the
small wall card. This is the existing architecture's artifact-provenance rule,
not permission to select/reuse an arbitrary web image.

Use indexed manifest storage and bounded iteration; do not load a global directory
of source images into memory. Convert one source asset at a time with explicit
input-byte/pixel limits before decode/rasterization. Proposed maintenance input
limits are 4 MiB and 1,024×1,024 raster pixels, with equivalent bounded SVG canvas
and disabled external resource fetches. Validate these with the chosen M6 converter;
no image-processing dependency or downloaded art is added in M1.

Stage manifest/converted blobs, validate every enabled artifact, then atomically
activate the manifest generation. Failed conversion/update retains last-good
approved mappings. Immutable bytes must not be overwritten under the old hash.
Descriptor/image availability cannot depend on an internet connection at runtime.

## 6. Generations and late asset requests

A flight response pins its reference and logo mapping during serialization, but
the ESP32's asset GET is a later request. Retain blobs for active and previous
mapping generations and do not delete old hashes immediately at activation.
Document a grace/cleanup policy in M6; current route-generation cleanup already
requires stopped readers. If an intentionally retired old asset eventually returns
404, render a badge rather than serving different pixels under the old path.

The response's `source_id` cites the exact asset-manifest generation used for the
descriptor. If operator/asset generations cannot be joined consistently, return
null logo rather than associating another airline's artwork. An updated valid
descriptor can change the current card's hash without resetting its dwell.

## 7. ESP32 memory and validation sequence

1. Validate descriptor bounds/type, exact operator ID match, same-Pi relative path,
   dimensions/format/order, declared byte length, and path/hash equality.
2. Check the four-entry hash cache. Never use an entry merely because it is the
   previous logo for the same aircraft hex.
3. On miss, fetch at most 1,152 bytes into a bounded staging buffer; detect a
   missing/extra byte, unexpected encoding, redirect or timeout.
4. Compute SHA-256 of those exact raw bytes and compare the advertised hash before
   displaying/caching. An invalid download cannot replace a good cache entry.
5. Decode/copy pixels using the format above into the renderer. No SVG/PNG/JPEG
   decoder, source-image resize, airline database or persistent global asset
   catalogue is needed on the ESP32.
6. Evict by bounded policy, initially LRU. Four pixel entries consume 4,608 bytes;
   account separately for one 1,152-byte staging buffer, keys/metadata, SHA state,
   task stacks and the existing 15,360-byte 160×32 RGB frame buffer.

Negative caching/retry state must also be bounded, initially at most 16 hashes
with a 60-second retry delay. Wi-Fi/Pi changes or a new content hash can trigger
a new attempt, without tight per-frame retries. These cache/timeout choices are
drafts for M3/M6 measurement; successful schema validation is not a heap budget.

Expiration of the aircraft card is independent of asset-cache age. A cached logo
does not permit showing an expired aircraft. Expired dated operator evidence
removes that logo association while useful fresh telemetry can remain.

## 8. Acceptance still pending

M6 must prove approved-image provenance, pixel colors/endian/layout, exact hashes,
same-origin HTTP behavior, failed/missing asset fallback, generation retention,
bounded cache/heap and coexistence with live flight polling and BLE. A mock logo
descriptor in an M1 fixture is not an approved airline image or an implemented
binary service. Physical matrix orientation and brightness/power checks remain
separate hardware acceptance work.
