# KODAK P210R Studio 1.8.1

Windows-Anwendung für den KODAK Mini 2 Retro P210R: Fotos gestalten, Polaroids beschriften, per Bluetooth drucken und den Druckversatz kalibrieren. Unabhängiges, KI-unterstützt entwickeltes Hobbyprojekt (vibe-coded).

## Installation

1. ZIP vollständig entpacken; Python 3.10+ verwenden.
2. Drucker per Bluetooth koppeln. Seriellen COM-Port in Windows prüfen (bei bisherigen Tests COM5).
3. `STARTEN.bat` ausführen.
4. Bilder importieren, Layout wählen und drucken.

## Neu: Druckkalibrierung

1. Oben rechts **Hilfe & Links → Druckkalibrierung…** wählen.
2. Mit **Testquadrat drucken** eine Referenzseite ausgeben. Das Testmuster ist exakt mittig auf dem Datenbild platziert und wird **immer ohne Kalibrierkorrektur** gedruckt.
3. Den fertigen Ausdruck ggf. von den Abreißstreifen befreien. Abstände **vom Papierrand zum schwarzen Quadrat** mit einem Lineal messen: links, rechts, oben und unten. In **Millimetern** eintragen.
4. Die Papierbreite und -höhe in mm prüfen (voreingestellt **54 × 86 mm** als Näherungswerte für den fertigen Ausdruck; tatsächliche Papiermaße sind maßgeblich).
5. **Korrektur berechnen** zur Prüfung und danach **Korrektur speichern**. Erneut das Quadrat drucken und die Messungen vergleichen.
6. **Zurücksetzen** setzt X und Y wieder auf null.

**Berechnung:** Horizontaler Versatz = (rechts − links) / 2 mm; vertikaler Versatz = (unten − oben) / 2 mm. Positive Werte verschieben das fertige Druckbild in die jeweilige positive Druckbildrichtung. Die Anwendung rechnet mm über die eingegebene physische Papiergröße in Bildpixel um.

**Wichtig:** Kalibrierung korrigiert die **Lage des gesamten Druckbildes auf dem Papier**, nicht die bewusst angelegte Größe des oberen oder unteren Polaroid-Randes. Bei absichtlich verschieden großen Polaroid-Rändern kann man deren Abstand nicht mit den vier Außenmaßen eines normalen Fotos gleichsetzen. Deshalb wird ein eigenes, symmetrisches Testquadrat benutzt.

Die globale Kalibrierung wird lokal unter `%APPDATA%\P210RStudio\calibration.json` (bzw. dem lokalen Konfigurationspfad) gespeichert. Bild- und Projektdateien bleiben unverändert. Die Korrektur wird **nach der für den Druck notwendigen Drehung** auf das Druck-JPEG angewendet, auch bei Stapeln und JPEG-Export.

## Druckphasen

Der Drucker meldet laut bisherigen Gerätetests: `FF` Druckstart, `05` Vorbereitung, `06` Gelb, `00` Magenta, `01` Cyan, `02` Schutzschicht, `03` abgeschlossen. Die Farbanimation bewegt sich von unten nach oben; **die Animation innerhalb einer Farbe ist nicht mechanisch gemessener Fortschritt**.

## Tests und Hinweise

`py -m unittest discover -s tests -v` — 30 Offline-Tests erfolgreich.

Der Druckdaten- und Bluetooth-Übertragungsablauf der zuvor funktionierenden Version bleibt erhalten. **Studio 1.8 und insbesondere der Kalibrier-Testdruck müssen noch am realen P210R geprüft werden.** Ein vollständig an den Drucker übermitteltes JPEG ist nicht zwingend eine mechanische Abschlussbestätigung.

Es sind **keine Beispielbilder** enthalten. Private Fotos, lokale Projektdateien und Ausgabeprotokolle gehören nicht ins GitHub-Repository.

Projekt: https://github.com/ManuelDeV-exe/kodak-P210R-Windows-Druck
## Update 1.8.1

Im Kalibrierfenster steht **TESTQUADRAT DRUCKEN** jetzt direkt oben. Das Fenster lässt sich bei hoher Windows-Anzeigeskalierung scrollen, damit auch die Berechnungs- und Speicherknöpfe erreichbar sind.
