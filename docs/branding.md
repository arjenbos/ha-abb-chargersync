# Branding assets

The integration includes the original ChargerSync branding from the supplied `ChargerSync_3.5.0_APKPure.xapk` package.

## Sources

- `brand/icon@2x.png` is an unchanged copy of the XAPK's 512×512 `icon.png`; `brand/icon.png` is a 256×256 copy resized from that image.
- `brand/logo.png` and `brand/logo@2x.png` are rendered from `res/drawable/cs_logo.xml` in the base APK.
- `brand/dark_logo.png` and `brand/dark_logo@2x.png` are rendered from `res/drawable-night/cs_logo.xml` in the base APK.
- Original Android vector files are retained as [chargersync-logo.xml](assets/chargersync-logo.xml) and [chargersync-logo-dark.xml](assets/chargersync-logo-dark.xml).

The vector paths and colors are preserved. The empty splash-screen viewport around the artwork is trimmed, and the paths are rendered to transparent PNGs. The standard logos are 540×256 pixels; their high-resolution variants are 1080×512 pixels. No artwork was redrawn or generated.

Files are stored in `custom_components/abb_chargersync/brand/`, following Home Assistant's [custom integration branding format](https://contributors.home-assistant.io/core/integrations/brands/). The README uses the same assets and selects the dark variant for dark color schemes. The installation ZIP includes the images, provenance documentation, and original vector sources.

The images retain the original ChargerSync branding. They do not change the integration's experimental status or imply official ABB support.
