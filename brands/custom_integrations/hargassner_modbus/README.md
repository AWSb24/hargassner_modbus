# Hargassner Modbus – brand assets

These images make the integration show a logo/icon instead of the "icon not
available" placeholder. Home Assistant loads them from
**brands.home-assistant.io**, not from the `custom_components` folder, so the
files must be submitted to the [home-assistant/brands](https://github.com/home-assistant/brands)
repository.

## Files
| File | Size | Purpose |
|------|------|---------|
| `icon.png` | 256×256 | square icon (integration card, device page) |
| `icon@2x.png` | 512×512 | hiDPI icon |
| `logo.png` | trimmed | horizontal logo (brand store, dialog headers) |
| `logo@2x.png` | trimmed | hiDPI logo |

All PNGs are RGBA; the icon fills the canvas (rounded tile) so it passes the
brands "square + trimmed" checks; the logos are cropped to their content.

## How to make them appear
1. Fork `home-assistant/brands`.
2. Copy this folder to `custom_integrations/hargassner_modbus/` in that fork
   (only the 4 PNGs are needed; not this README or the generator).
3. Open a pull request. After it is merged and the CDN updates, the card shows
   the icon automatically (a HA restart / cache refresh may be needed).

The artwork is an original flame mark (not Hargassner's trademarked logo);
"Hargassner" is used descriptively as the device manufacturer, like other brand
integrations.

## Regenerating
`python _generate_assets.py` (requires Pillow). Edit colours/shape there.
