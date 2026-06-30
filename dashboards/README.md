# Hargassner Anlagenschema (Floorplan)

Ein interaktives Hydraulik-Schema, das sich **automatisch an die Anlage anpasst**:
nicht vorhandene Komponenten (Heizkreis, Boiler, Frischwasserstation, …) blenden
sich aus, sobald ihr Master-Register „Nicht vorhanden" meldet. Funktioniert ideal
mit dem **Preset „Automatisch"** der Integration.

![Vorschau](preview.png)

## Voraussetzungen
- Die Integration **Hargassner Modbus** ist eingerichtet.
- HACS ist installiert.

## Installation
1. **HACS → Frontend → „Floorplan"** installieren (Repo `ExperienceLovelace/ha-floorplan`), danach Browser neu laden.
2. Datei `hargassner_floorplan.svg` nach **`config/www/hargassner/hargassner_floorplan.svg`** kopieren (Ordner ggf. anlegen).
3. In einem Dashboard eine **Manuelle Karte** hinzufügen und den Inhalt von `hargassner_floorplan.yaml` einfügen.

## Funktionen
- **Live-Werte** für Kessel, Pelletlager, Zentralpuffer, Heizkreis 1, Frischwasserstation 1, Boiler 1.
- **Auto-Ausblenden** ganzer Blöcke je nach vorhandener Komponente (Master-Sensor `= "Nicht vorhanden"`).
- **Pumpe Heizkreis 1** wird grün, wenn sie läuft; die **Flamme** dimmt bei „Aus/Bereit".
- **Klick** auf ein Element → Mehr-Infos-Dialog; **Hover** zeigt den Wert.
- Heizkreis 1 ist **direkt am Kessel** angeschlossen (Leitungsführung im SVG).

## Anpassen
- **Entity-IDs:** Die YAML geht vom Standard-Gerätenamen „Hargassner Heizung" aus
  (Präfix `hargassner_heizung_`). Bei umbenanntem Gerät den Präfix in der YAML ersetzen.
- **Weitere Komponenten** (Heizkreis 2–6/A/B, Boiler 2–3/A/B, FWS 2–4, Zusatzpuffer,
  Kaskade): im SVG einen weiteren `<g id="g_xxx">`-Block ergänzen und in der YAML
  analoge `text_set`-/`class_set`-Regeln hinzufügen (Master-Sensor `…_heizkreis_2`,
  `…_boiler_2`, `…_frischwasserstation_2`, …).
- **Farben/Layout:** alles im `<style>`-Block bzw. den Koordinaten des SVG.

## Dateien
- `hargassner_floorplan.svg` – das Schema (benannte Elemente: Werte + `g_*`-Gruppen).
- `hargassner_floorplan.yaml` – Floorplan-Karte mit den Bindungsregeln.
