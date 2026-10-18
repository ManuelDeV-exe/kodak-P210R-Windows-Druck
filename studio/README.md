# KODAK P210R Studio 1.0

Lokale Windows-Oberfläche zum Vorbereiten und Drucken von Fotos mit dem erfolgreich getesteten KODAK Mini 2 Retro P210R. Die Bluetooth-Druckroutine `driver/print_photo.py` ist **bytegleich mit V2.3**; sie wurde nicht angepasst.

## Start

1. ZIP komplett entpacken.
2. Drucker via Bluetooth koppeln; richtigen seriellen COM-Port ermitteln (bisher COM5).
3. `STARTEN.bat` doppelklicken. Beim ersten Start werden Pillow und pyserial installiert. Python 3 muss installiert sein.
4. JPG/PNG/WebP/BMP/TIFF hinzufügen oder einen Ordner auswählen.
5. Foto markieren und optional drehen, Helligkeit, Kontrast, Sättigung und Zuschnitt/Einpassen einstellen. Kopienzahl je Foto angeben, Reihenfolge mit Pfeiltasten ändern.
6. `Stapel drucken` anklicken. Bilder werden jeweils in **640 × 1024 Pixel** und JPEG gewandelt, anschließend einzeln über V2.3 an COM5 übertragen.

Alternativ: `py -m pip install -r requirements.txt`, danach `py app.py`.

## Hinweise

- Die Bluetooth-Verbindung ist exklusiv: KODAK-App währenddessen schließen.
- Eine Übertragung kann länger dauern. Der V2.3-Treiber beobachtet den Drucker standardmäßig bis zu 60 Sekunden nach Abschluss der Bildübertragung, wenn nicht vorher ein Abschlussmarker ankommt.
- Ohne gemeldeten Abschlussmarker heißt „Übertragen“ **nicht automatisch** „Foto physisch fertig gedruckt“. Beim ersten Stapel bitte die Reihenfolge unter Aufsicht prüfen.
- Beim Druckfehler stoppt die Warteschlange. `Nach aktuellem Foto stoppen` bricht die laufende Bluetooth-Übertragung absichtlich **nicht** mittendrin ab.
- Erzeugte JPEGs und JSON-Protokolle befinden sich je Stapel unter `output/Datum_Uhrzeit/`.
- Statusabfragen sind optional und standardmäßig deaktiviert, genau wie beim erfolgreichen V2.3-Versuch.
- Der Workflow druckt Fotos unabhängig von deren ursprünglicher Auflösung; beim Modus „Füllen“ wird bei abweichendem Seitenverhältnis mittig beschnitten. Bei „Ganzes Bild“ bleiben gegebenenfalls weiße Ränder.
- Die konkrete Mechanik und Wartung von Papier/Tinte/Kassette bleibt Sache des Druckers.