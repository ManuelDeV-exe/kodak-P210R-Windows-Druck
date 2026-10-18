# KODAK P210R Studio 1.6

Eine lokale Windows-App zum Bearbeiten und Drucken von Fotos über den Bluetooth-COM-Port des KODAK P210R. Unabhängiges, mit KI-Unterstützung entwickeltes Hobbyprojekt.

## Neu in Version 1.6

- Modernere, blaue Oberfläche mit drei **getrennten Seiten**: Druckwarteschlange, Fotogestaltung und Druckprotokoll. Keine aufklappbaren Akkordeons.
- Warteschlange und Fotogestaltung sind nicht mehr gleichzeitig im Hauptfenster; per Navigation wechseln, Doppelklick auf ein Foto öffnet den Editor.
- Bearbeitung in einem eigenen Arbeitsbereich mit großer Vorschau und **scrollbaren Einstellungen**; bei schmaleren Fenstern wandern die Einstellungen unter das Bild.
- Druckprotokoll öffnet sich beim Druckstart automatisch; das separate Druckfenster zeigt das aktuelle Foto.
- **Farbanimation von unten nach oben**, passend zu tatsächlich erkannten Gelb-, Magenta-, Cyan- und Schutzschicht-Statusmeldungen. Die Animation ist illustrativ, keine gemessene Druckgeschwindigkeit.
- Feinregler, Projektdateien, Polaroid-Layouts, EXIF-Datum und weitere Bearbeitung aus den vorherigen Versionen bleiben erhalten.

## Start

1. Python 3.10 oder neuer auf Windows installieren.
2. Drucker koppeln und seriellen COM-Port nachsehen (in unserem Test COM5).
3. `STARTEN.bat` doppelklicken; der erste Start installiert Pillow und pyserial.
4. Bilder in **Druckwarteschlange** hinzufügen. Per Doppelklick oder Navigation zu **Fotogestaltung** wechseln.
5. Für einen Ausdruck auf **Stapel drucken** klicken. Dabei wird das **Druckprotokoll** sichtbar; zusätzlich öffnet sich das Druckfenster.

## Hinweise

- Die bewährten Druckdatenpakete und die Bluetooth-Übertragung bleiben auf der Version 2.3 basierend.
- Der Drucker meldet unter anderem: `FF` Vorbereitung, `05` Gelb, `06` Magenta, `00` Cyan, `01` Schutz, `02` unbekannt, `03` Abschluss.
- Der tatsächliche Statuswechsel bestimmt die Farbe. Die Geschwindigkeit des farbigen Balkens ist **keine** Hardwaremessung.
- Die Bildverarbeitung erstellt 640 × 1024 Pixel. Der Abreißstreifen sitzt an der kurzen Papierseite.
- Eigene Fotos/Projekte/Logs bleiben lokal; das Repository/ZIP enthält keine Beispielbilder.
- Die neue Oberfläche muss noch auf Windows mit dem Drucker getestet werden.

**Repository:** https://github.com/ManuelDeV-exe/kodak-P210R-Windows-Druck