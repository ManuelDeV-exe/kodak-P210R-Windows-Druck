<div align="center">

![KODAK P210R Studio](docs/images/hero.svg)

# KODAK P210R Studio

**Fotos am Windows-PC bearbeiten, gestalten und ohne die offizielle Smartphone-App per Bluetooth auf dem KODAK Mini 2 Retro P210R drucken.**

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-Desktop-0078D4?logo=windows&logoColor=white)
![Studio](https://img.shields.io/badge/Studio-1.4-6e7be8)
![Drucktreiber](https://img.shields.io/badge/Bluetooth--Druck-V2.3%20erfolgreich-2b9348)

</div>

## Was ist das?

**KODAK P210R Studio** ist eine eigenständige Python-Desktop-Anwendung für den Fotodrucker **KODAK Mini 2 Retro P210R**. Sie bietet eine Bildvorschau, einfache Bildbearbeitung, verschiedene Rahmenlayouts und eine Druckwarteschlange für mehrere Fotos.

Die eigentliche Bluetooth-Druckroutine wurde aus einer eigenen Protokollaufzeichnung rekonstruiert. **Ein vollständiger Ausdruck mit der Python-Druckroutine V2.3 wurde auf einem P210R erfolgreich getestet.** Die grafische Anwendung und insbesondere der Stapeldruck sind noch am Gerät zu erproben.

## Drucklayouts

![Vorschau der drei Drucklayouts](docs/images/layouts.svg)

| Layout | Beschreibung |
| --- | --- |
| **Ohne Rahmen** | Foto ohne zusätzlichen weißen Rahmen. |
| **Weißer Rand** | Klassischer Druck mit einstellbarer Randbreite. |
| **Polaroid 1:1,2** | Hochformatige Fotofläche mit weißem Platz für Text. |
| **Polaroid 1:1,4** | Längere Fotofläche und zusätzlicher weißer Textbereich. |\n| **Polaroid 1:1,6** | Noch schmalere Fotofläche und mehr Platz für Text. |

Die Formate **1:1,2 und 1:1,4** beziehen sich auf das Verhältnis **Breite : Höhe der inneren Fotofläche**. Das physische Papierformat bleibt unverändert. Die Druckbilder werden auf **640 × 1024 Pixel** vorbereitet.

## Funktionen in Studio 1.4

- Bilder einzeln oder aus ganzen Ordnern importieren.
- Bildvorschau mit unmittelbarer Anzeige der Bearbeitungen.
- Helligkeit, Kontrast und Sättigung ändern.
- Bilder drehen, einpassen oder passend zuschneiden.
- Weißrand und beide Polaroid-Layouts auswählen.
- Freie Bildunterschrift in den weißen Polaroid-Bereich schreiben.
- Druckwarteschlange mit Reihenfolge und Kopienzahl.
- Stapeldruck über Bluetooth-COM-Port.
- Druckbild optional um 180° drehen.
- Aktivitätsanzeige und lokale Druckprotokolle.

**Hinweis zum Abreißstreifen:** Beim Papierauswurf sitzt der Streifen **links**. Die Vorschau markiert diese Seite; die Markierung wird nicht mitgedruckt.

Die animierte Anzeige zeigt **Aktivität**, keinen exakt gemessenen Druckfortschritt.

## Installation und erster Druck

1. Dieses Repository als ZIP herunterladen oder klonen.
2. **Python 3.10 oder neuer** unter Windows installieren.
3. Den KODAK P210R einschalten und über Bluetooth mit Windows koppeln.
4. Den Ordner **`studio`** öffnen.
5. **`STARTEN.bat`** doppelklicken. Beim ersten Start werden die erforderlichen Python-Pakete installiert.
6. Den **ausgehenden seriellen Bluetooth-COM-Port** im Studio einstellen. Im ursprünglichen Testaufbau war dies **COM5**; auf anderen PCs kann er anders heißen.
7. Foto hinzufügen, Layout auswählen und zunächst **einen einzelnen Probedruck** ausführen.

Alternativ in der Windows-Eingabeaufforderung:

```bat
cd studio
py -m pip install -r requirements.txt
py app.py
```

**Wichtig:** Die originale KODAK-App darf den Drucker während des Druckvorgangs nicht gleichzeitig verwenden. Beim ersten Stapeldruck die Ausgabe beaufsichtigen.

## So arbeitet das Studio

![Ablauf vom Foto bis zum Ausdruck](docs/images/workflow.svg)

1. **Import:** Das Studio lädt ein Foto oder eine ganze Bildsammlung in die Warteschlange.
2. **Bearbeitung:** Für jedes Bild werden Layout, Beschnitt, Farbe und optional eine Beschriftung gewählt.
3. **Rendering:** Die Anwendung rendert daraus lokal ein JPEG mit **640 × 1024 Pixeln**.
4. **Druckauftrag:** Der unveränderte **V2.3-Treiber** in `studio/driver/print_photo.py` überträgt die Bilddaten über den Bluetooth-COM-Port.
5. **Stapeldruck:** Weitere Bilder bzw. Kopien werden der Reihe nach gesendet.

Für die Bildbearbeitung und den Druck ist nach Installation der Abhängigkeiten keine Internetverbindung erforderlich.

## Projektstruktur

```text
kodak/
├── README.md
├── docs/
│   └── images/
│       ├── hero.svg
│       ├── layouts.svg
│       └── workflow.svg
└── studio/
    ├── app.py
    ├── driver/
    │   └── print_photo.py
    ├── STARTEN.bat
    ├── requirements.txt
    ├── .gitignore
    ├── tests/
    └── README.md
```

## Tests

Die Offline-Tests können so gestartet werden:

```bat
cd studio
py -m unittest discover -s tests -v
```

**Stand:** Der Bluetooth-Einzeldruck mit V2.3 ist erfolgreich erprobt; für alle neuen Layoutvarianten und lange Stapel steht der vollständige Hardwaretest noch aus.

## Neu in Studio 1.4

- **Mit der Maus zoomen und verschieben:** Mausrad in der Vorschau und Ziehen mit linker Maustaste. Der Bildausschnitt wird mitgedruckt.
- **Eigenes App-Icon:** Kamerasymbol im Windows-Fenster.
- **Schriftwahl für Polaroids:** Standard bleibt vorausgewählt; zusätzlich Segoe UI, Arial, Georgia, Times New Roman und Consolas.
- **Bearbeitung zurücksetzen:** Fotoeinstellungen einschließlich Zoom, Layout, Beschriftung und Schriftauswahl zurücksetzen.
- **Abhakbare Warteschlange:** Jedes Foto einzeln vom nächsten Stapeldruck ausschließen.
- **Projektdateien:** Bildreihenfolge, Einstellungen, Kopien, Druckauswahl und COM-Port in `*.p210r.json` speichern und laden. Projekte enthalten **nur Verweise auf Bilddateien**, nicht die Bilder selbst.
- **EXIF-Datum:** Aufnahmedatum automatisch als Polaroid-Beschriftung übernehmen; ohne Metadaten bleibt der manuelle Text.
- **KODAK-Link:** Herstellerwebseite aus der Anwendung öffnen.

**Neu in 1.3:** Bei Polaroid-Drucken wird das Foto für die tatsächliche Papierausgabe automatisch um 180° gedreht, während die Vorschau aufrecht bleibt. Bei Bedarf kann die Drehrichtung umgekehrt werden. Zusätzlich steht Polaroid 1:1,6 zur Verfügung. Die V2.3-Bluetooth-Druckroutine bleibt unverändert. Acht Offline-Tests wurden erfolgreich ausgeführt; die neue Oberfläche und längere Druckstapel sind noch am Gerät zu testen.

## Studio 1.4: Weitere Bearbeitung und Live-Druckphasen

- **Weitere Bearbeitung:** Lightroom-ähnlicher Dialog mit Belichtung, Lichtern, Tiefen, Farbtemperatur, Schärfe, Live-Vorschau und Vorher/Nachher.
- **Abreißstreifen:** Vorschau markiert nun die kurze Papierseite (unten beim Hochformat) statt irrtümlich die linke lange Kante.
- **Verschieben ohne Zoom:** Bildausschnitt mit der Maus verstellen; zusätzliche Schaltfläche zum Zentrieren.
- **Alle Fotoeinstellungen zurücksetzen:** einschließlich Kopien und Druckauswahl.
- **Hilfe & Links:** KODAK-Website und GitHub im Untermenü.
- **Statusabfragen standardmäßig aktiv:** dekodierte tatsächliche Antworten: `FF` Vorbereitung, `05` Gelb, `06` Magenta, `00` Cyan, `01` Schutzschicht, `02` unbekannt, `03` abgeschlossen. Zuordnung basiert auf Praxiserfahrungen, nicht offizieller Dokumentation. Es werden keine fiktiven Fortschrittswerte erzeugt.

**10 Offline-Tests bestanden.** Die seriellen Druckdatenpakete der erfolgreichen V2.3-Übertragung wurden nicht verändert; ausschließlich die Ausgabe/Dekodierung von Statusmeldungen wurde ergänzt. Neue GUI-Funktionen sind noch vor Ort zu testen.

## Datenschutz

**In diesem Repository befinden sich keine privaten Test- oder Beispielfotos.** Die Grafiken dieser README sind **eigens erstellte SVG-Illustrationen**, keine persönlichen Fotos. Die `studio/.gitignore` schließt typische Bilddateien sowie lokale Druck- und Protokolldateien aus.

## Hinweise

Dies ist ein unabhängiges Community-/Entwicklungsprojekt und **keine offizielle Software von KODAK**. Druckprotokoll und Hardwareverhalten können je nach Firmware oder Bluetooth-Konfiguration abweichen.

Weiterführende Hinweise: [Studio-Dokumentation](studio/README.md).
