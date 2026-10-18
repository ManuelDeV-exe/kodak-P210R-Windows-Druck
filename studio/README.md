# KODAK P210R Studio 1.1

Windows-App mit modernerer Tkinter-Oberfläche, lebendiger Druckanzeige, Foto-Vorschau, Stapelverarbeitung und anpassbaren Weißrand- und Polaroid-Layouts. **Der erfolgreich getestete Bluetooth-Treiber `driver/print_photo.py` ist unverändert aus V2.3 übernommen.**

## Start

1. ZIP entpacken, Drucker per Bluetooth verbinden (bisher COM5).
2. `STARTEN.bat` ausführen (Python 3.10+ erforderlich). Oder `py -m pip install -r requirements.txt` und `py app.py`.
3. Fotos/Ordner hinzufügen. Foto links auswählen und rechts bearbeiten.
4. Druckstil auswählen: *Ohne Rahmen*, *Foto mit weißem Rand*, *Polaroid 1:1,2* oder *Polaroid 1:1,4*.
5. Randbreite einstellen; bei Polaroids optional eine kurze Bildunterschrift eingeben. Die Vorschau zeigt das fertig gerenderte Bild.
6. **Abreißstreifen:** Beim physischen Auswurf befindet sich der abtrennbare Streifen links. Die gestrichelte Markierung in der Vorschau kennzeichnet diese Seite, ist aber **nicht** Teil der Datei. Falls die Orientierung nicht passt, *Druckbild um 180° drehen* aktivieren; die Vorschau aktualisiert sich sofort.
7. Kopienzahl, Bildkorrekturen und Reihenfolge einstellen. *Stapel drucken* ausführen.

## Layout-Logik

- P210R-Ausgabedateien haben immer **640 × 1024 Pixel**. Die Druckhardware und deren Position des Streifens werden durch die App nicht verändert.
- Beim klassischen weißen Rand ist die Breite über den Schieberegler einstellbar.
- Polaroid **1:1,2** und **1:1,4** bezeichnen das *Verhältnis Breite : Höhe der inneren Fotofläche*. Bei beiden Layouts wird unten weißer Platz für Text gelassen; beim 1:1,4-Layout mehr.
- Mit *Füllen* wird die innere Bildfläche beschnitten; mit *Ganzes Bild* wird sie ohne Beschnitt eingepasst.
- Polaroid-Text wird in den größeren unteren Rand geschrieben; je nach Windows-Font erfolgt eine handschriftähnliche oder normale Schriftdarstellung.
- Hochformat-Ausrichtung und Weißräume sind Vorschau-Vorgaben, keine separate Papierauswahl.

## Sicherheit, Grenzen und Datenschutz

- **Keine Beispielbilder im Repository oder ZIP.** Bei Tests werden Fotos nur lokal geladen und verarbeitet.
- `.gitignore` schließt gängige Bildtypen, private Daten, Logs und den Ordner `output/` aus.
- Bearbeitungen sind je Bild gespeichert; während eines Druckstapels sind neue Bearbeitungen nicht wirksam.
- Bluetooth exklusiv verwenden, die originale KODAK-App geschlossen halten.
- Ein erfolgreicher Schreibvorgang beweist nicht zwangsläufig einen abgeschlossenen Ausdruck. Stapeleinsätze unter Aufsicht testen und erst erweitern, wenn mehrere Ausgaben korrekt funktionieren.
- Die animierte Fortschrittsanzeige zeigt *Aktivität*, **keinen verlässlichen Prozent-Fortschritt**.
- Python-Tests: `py -m unittest discover -s tests -v`.