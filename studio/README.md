# KODAK P210R Studio 1.7

Eine Windows-Anwendung für Bildbearbeitung, Polaroid-Layouts und Bluetooth-Fotodruck mit dem KODAK Mini 2 Retro P210R. Unabhängiges Hobbyprojekt, mit KI-Unterstützung (vibe-coded) entwickelt.

## Neu in 1.7

Das animierte Druckfenster bekommt jetzt echte Ereignisse vom Python-Drucktreiber:

- **Bildübertragung:** Der Drucktreiber gibt die bestätigte übertragene Bytezahl aus. Die Anwendung zeigt den daraus berechneten Übertragungsfortschritt in Prozent.
- **Druckphasen:** Sobald ein Statuspaket `04 03 01 01 ...` vom Drucker eintrifft, wechselt das Fenster zur gemeldeten Phase: `FF` Vorbereitung, `05` Gelb, `06` Magenta, `00` Cyan, `01` Schutzschicht, `02` unbekannt, `03` fertig.
- **Animation:** Während einer Farbphase wandert die farbige Zone **von unten nach oben**. Die Bewegung ist *nur eine Visualisierung*; es gibt im analysierten Protokoll keine gesicherte Prozentangabe innerhalb einer Farbe. Die Animation stoppt bei maximal 94 % und beginnt erst beim nächsten echten Statuscode neu.
- **Diagnose:** Wenn über den beobachteten Zeitraum kein Farbstatus kommt, meldet die Anwendung das ausdrücklich. Der Druckbericht enthält die empfangenen Rohpakete.

Die Befehle zur Bildübertragung und der bestätigte V2.3-Druckablauf bleiben unverändert. Die zusätzliche Konsolenausgabe ist ausschließlich für die Benutzeroberfläche gedacht.

## Anwendung starten

1. ZIP vollständig entpacken und `STARTEN.bat` doppelklicken.
2. Drucker koppeln und den seriellen Bluetooth-Port einstellen (beim bisherigen Test COM5).
3. Foto(s) hinzufügen, Gestaltung bearbeiten und drucken.
4. Das Druckfenster und das automatisch geöffnete Protokoll beobachten.

Für einen direkten Diagnoselauf auf COM5 (mit selbstgewählter lokaler Bilddatei) geht auch:

```cmd
py driver\print_photo.py --send --port COM5 --image "C:\Pfad\zum\Foto.jpg" --poll --emit-phases
```

Die JSON-Berichte liegen bei Studiostapeln im Unterordner `output/` des jeweiligen Auftrags. Wenn der Drucker arbeitet, aber die Farben nicht gemeldet werden, ist genau dieser Bericht für die nächste Analyse hilfreich.

## Was die Fortschrittswerte aussagen

- Der Prozentwert während der **Übertragung** bezieht sich auf gesendete/abgedeckte JPEG-Bytes, nicht auf den mechanischen Druck.
- Die **Farbphase** beruht auf einer tatsächlichen Antwort des Druckers.
- Der Balken *innerhalb* einer Farbphase ist weiterhin nicht auf einen Encoder oder eine reale Prozentmeldung synchronisiert. Eine echte Feinmessung ist mit dem derzeit bekannten Protokoll nicht möglich.
- `02` bleibt absichtlich ohne behauptete Bedeutung.

23 Offline-Tests bestanden. Neue Statusanzeige noch nicht am echten Drucker bestätigt.

Private Fotos und Projektdateien werden nicht mitgeliefert. Die Software ist keine offizielle KODAK-Anwendung.

Projekt: https://github.com/ManuelDeV-exe/kodak-P210R-Windows-Druck

## Polaroid 1:1,6 – schmale Seitenränder

Bei diesem Layout füllt das Foto die Breite fast vollständig aus (ca. 12–35 Pixel Rand je Seite). Der weiße Bereich für die Beschriftung bleibt unten erhalten. **1:1,6 bezeichnet dabei das Gesamtformat des 640 × 1024-Pixel-Ausdrucks**, nicht das Verhältnis der inneren Fotofläche. Die Druckroutine selbst ist unverändert.