# KODAK P210R Studio 1.5

Lokale Windows-Anwendung mit Fotovorschau, Bildbearbeitung, Polaroid-Layouts und Druckwarteschlange für den KODAK Mini 2 Retro P210R. Der **nachweislich funktionierende V2.3-Bluetooth-Drucktreiber** (`driver/print_photo.py`) bleibt unverändert.

## Start

1. Bluetooth-Drucker in Windows koppeln und zugehörigen seriellen COM-Port ermitteln (im bisherigen Test COM5).
2. ZIP vollständig entpacken und `STARTEN.bat` doppelklicken. Python 3.10+ benötigt. Alternativ `py -m pip install -r requirements.txt` und `py app.py`.
3. Bilder über *Bilder hinzufügen* oder *Ordner hinzufügen* importieren.
4. Foto auswählen, Drucklayout bearbeiten, Kopienzahl einstellen.
5. Über das Kästchen **☑** in der Tabelle Fotos für den nächsten Stapeldruck einschließen bzw. abwählen. `Stapel drucken` sendet nur angehakte Fotos.

## Neu in Version 1.2

- **Maus-Zoom**: Mit dem Mausrad über der Bildvorschau vergrößern oder verkleinern (1× bis 8×). Bei vergrößertem Bild **linke Maustaste gedrückt halten und ziehen**, um den Ausschnitt zu verschieben. Das wird im Projekt gespeichert und wirklich auf das Druckbild angewandt.
- **App-Icon**: Eigenes Kamera-Symbol im Fenster, ohne externe Grafikdatei oder ein Benutzerfoto.
- **Schriftwahl**: `Standard` (wie bisher) sowie Segoe UI, Arial, Georgia, Times New Roman und Consolas. Fehlende Schriftdateien erhalten eine Ersatzschrift.
- **Zurücksetzen**: `Bearbeitung zurücksetzen` stellt Bildbearbeitungsparameter, Zoom und Schrift auf Standard zurück.
- **Abhakbare Warteschlange**: Auf das Häkchen in der ersten Tabellenspalte klicken. Deaktivierte Bilder werden nicht gedruckt.
- **Projekte speichern/öffnen**: Projekt als `*.p210r.json` mit Reihenfolge, Kopienzahl, Bildern, Layouts, Bearbeitungen, Druckauswahl und COM-Port speichern; später wieder laden. **Die Projektdatei enthält Bildpfade, keine eingebetteten Bilder.** Wird sie mit den Bildern verschoben, müssen relative Pfade erhalten bleiben. Fehlende Bilder werden beim Laden gemeldet.
- **EXIF-Datum**: Für Polaroids `EXIF-Datum` aktivieren. Die Anwendung nutzt das im Foto hinterlegte Aufnahme-/Digitalisierungsdatum (Format `TT.MM.JJJJ`). Fehlen Metadaten, bleibt der manuell eingegebene Text erhalten.
- **KODAK-Link**: Schaltfläche `KODAK ↗` öffnet die Webseite des Foto-Drucker-Herstellers im Browser.

## Formate und Bedienung

- Druckdatei: **640 × 1024 Pixel**, unabhängig vom Layout. Der Abreißstreifen befindet sich bei der Ausgabe **an der kurzen Seite**. Die Markierung in der Vorschau wird nicht mitgedruckt.
- Rahmen: ohne Rand, weißer Rand, Polaroid **1:1,2**, **1:1,4** oder **1:1,6**, jeweils mit einstellbarer Rahmenbreite bzw. Text.
- `Füllen (Beschnitt)` vergrößert das Foto auf die Bildfläche; `Ganzes Bild` zeigt das komplette Motiv, solange kein zusätzlicher Mauszoom gesetzt ist.
- **Stapelverarbeitung** über die bewährte Bluetooth-Seriellroutine. Die animierte Fortschrittsanzeige zeigt nur Aktivität, keinen exakt gemessenen Prozentfortschritt. Druckaufträge während der ersten Tests beaufsichtigen.
- Bearbeitungen sind pro Bild gespeichert, während eines laufenden Stapels wird ein Snapshot verwendet.

## Datenschutz und Tests

- **Keine privaten Beispielbilder im Quellpaket oder auf GitHub.** `.gitignore` schließt Fotos, Ausgabedateien und lokale Projektdateien aus.
- Lokale Projekte können private Dateipfade enthalten: nicht unbedacht veröffentlichen.
- Tests: `py -m unittest discover -s tests -v` aus dem `studio`-Ordner.
- Der Einzeldruck mit dem V2.3-Treiber wurde am Drucker bestätigt. Neue UI-Funktionen und längere Stapel sind vor Ort noch zu testen.

## Neu in Version 1.3

- Zusätzliches Polaroid-Format **1:1,6**, mit mehr Platz unter dem Foto für Text.
- **Korrigierte Druckausrichtung:** Vorschau zeigt Polaroid-Schriftbereich unten; für die Papierausgabe werden Polaroids automatisch um 180 Grad gedreht, sodass der Bereich beim fertigen Bild unten erscheint.
- **Druckausrichtung umkehren** überschreibt die automatische Drehrichtung, falls bei anderer Geräteausrichtung erforderlich. Die Vorschau bleibt dabei immer aufrecht.
- Der unveränderte V2.3-Treiber wird verwendet; die Korrektur erfolgt ausschließlich am JPEG vor dem Drucken.
- Achtung: Drehrichtung aufgrund des Anwenderfeedbacks korrigiert, mit einem Probedruck zu verifizieren.

## Neuerungen in Version 1.4

- **Weitere Bearbeitung:** separater Dialog mit Live-Vorschau, Vorher/Nachher-Vergleich und Reglern für Belichtung, Lichter, Tiefen, Farbtemperatur und Schärfe. Die Effekte sind Lightroom-inspiriert, jedoch eigene vereinfachte Bildberechnungen.
- **Hilfe & Links:** KODAK-Webseite, GitHub-Repository und GitHub-Anleitung unter einem Menü oben rechts. Der bisherige KODAK-Knopf bei den Schrifteinstellungen entfällt.
- **Abreißstreifen:** Markierung unten an der kurzen Seite der hochformatigen Druckvorschau. Es ist nur eine grafische Hilfe, kein Bestandteil des JPEG.
- **Zurücksetzen:** setzt alle Einstellungen des ausgewählten Bilds einschließlich Kopienzahl, Druckhaken und erweiterter Korrekturen auf Standard zurück.
- **Verschieben ohne Zoom:** Die Mausverschiebung funktioniert auch bei Faktor 1,0; bei Bedarf wird geringfügig in das Bild hineingeschnitten, damit ein sichtbarer Versatz möglich ist.
- **Bild zentrieren:** setzt die Verschiebung auf null.

Der unveränderte Drucktreiber V2.3 ist weiterhin unter `driver/print_photo.py` enthalten.

## Druckphasen in Studio 1.4

Mit aktivierten Statusabfragen (Vorgabe) zeigt Studio erkannte Live-Phasen aus den tatsächlichen Bluetooth-Antworten: `FF` Vorbereitung, `05` Gelb, `06` Magenta, `00` Cyan, `01` Schutzschicht, `02` unbekannt, `03` abgeschlossen. Die Bezeichnungen folgen den Beobachtungen am Gerät und sind noch nicht durch Herstellerprotokolle bestätigt. Ein separater `04 06` Abschlussmarker wird ebenfalls erkannt. Statusabfragen können abgeschaltet werden. Keine künstliche Fortschrittsprozent-Anzeige.

Die serielle Übertragungsroutine des bewährten V2.3-Treibers bleibt in ihren Datenpaketen unverändert; ergänzt wurde allein die passive Status-Dekodierung und ihre Ausgabe für die Studio-Oberfläche.

## Neu in Studio 1.5: Bildposition fein einstellen

Unterhalb der Bildvorschau gibt es jetzt zwei Schieberegler für die **horizontale** und **vertikale** Bildverschiebung (jeweils -100 % bis +100 %). Neben jedem Regler sind **− / +**-Schaltflächen für Korrekturen um **1 Prozentpunkt**. Die Regler synchronisieren sich beim Verschieben mit der Maus, bei Bildwechsel und beim Zentrieren. Die Position wird wie bisher als `pan_x` / `pan_y` pro Bild in Projektdateien gespeichert. Auch ohne manuell eingeschalteten Zoom lässt sich das Bild fein verschieben. Die Bluetooth-Druckroutine bleibt unverändert.

## Neu in Studio 1.5

- Zwei Positionsregler unter der Vorschau, jeweils für horizontal und vertikal. Mit den Tasten **− / +** lässt sich der Bildausschnitt in 1-%-Schritten verschieben; auch ohne manuell gesetzten Zoom. Mausverschiebung und Regler zeigen dieselbe Position an.
- Während des Druckens öffnet sich ein separates Fenster mit dem aktuellen Foto. Sobald der Drucker eine Farbphase meldet, läuft eine farbige Überlagerung von oben nach unten über die Vorschau: Gelb, Magenta, Cyan oder Schutzschicht. Die Animation zeigt **keinen echten Druckfortschritt** und beeinflusst nicht die Druckdaten.
- Aufgeräumtere Bereiche **01 Druckwarteschlange**, **02 Foto gestalten** und **03 Ausgabe & Druck** sowie abgestimmte Farben und größere Bedienelemente.
- Die Anzeige des Abreißstreifens weist jetzt auch während des Druckens auf die kurze Papierseite hin.

Der originale V2.3-Datenversand bleibt erhalten. Die Druckphasen beruhen auf den tatsächlich erhaltenen Statusantworten; wenn der Drucker keine Antwort liefert, wird auch keine fiktive Druckphase vorgetäuscht.

Das Studio wurde als Hobbyprojekt mit KI-Unterstützung (vibe-coded) entwickelt. Die Bedienoberfläche und der Ablauf werden anhand praktischer Drucktests laufend verbessert.