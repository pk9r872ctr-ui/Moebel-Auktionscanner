# Vollkosten- und Unsicherheitsmodell Auftrag 03

`extended_economics.assess_extended(listing, assumptions, plan,
review_confirmed=False, now=None)` ergänzt die bestehenden Schnittstellen, mit unveränderten bisherigen Rechenschnittstellen. `plan` ist ein `ExtendedPlan`, dessen
Dictionary oder `None`. Die Ausgabe enthält `status`, `blockers`, `economics`,
`technical_priority` und eine Kopie sämtlicher `inputs` für Nachvollziehbarkeit.

Ohne vollständigen Plan gibt es keinen Vollkosten-Score. Unbekannte Zusatzkosten
sind `None`; tatsächliche Nullkosten müssen ausdrücklich eingetragen werden. Ein
manuell geprüfter Plan braucht eine Referenz, eine Methode und Herkunft. Der
Schalter zur Prüfung macht geschätzte Quelldaten nicht automatisch zu beobachteten
Daten. Boolesche Vorsteuerflags werden im Finanzkern strikt geprüft; Zahlen im Vollkostenplan sind auf 1 Milliarde begrenzt, um ungültige Rechenbereiche auszuschließen. Die bisherigen Aktualitäts-, Steuer- und Gebühren-Gates bleiben bestehen.

## Eingaben und Grenzen

Transport, Aufbereitung, Lagerung und Entsorgung stammen ausschließlich aus dem
Los. Abholung, Demontage, Verladung, Verkaufsgebühren, Fixgebühren und
Finanzierungskosten im Plan sind **zusätzliche Bruttokosten**. Sind sie schon im
Los enthalten, ist das entsprechende Planfeld ausdrücklich null einzutragen und
die Abgrenzung in der Referenz festzuhalten. Automatische Rechnungsinterpretation
oder Erkennung versteckter Kosten erfolgt nicht. Verkaufsgebühren sind ein
expliziter absoluter Kostenbetrag, keine erfundene Plattformregel.

Zusätzliche Vorsteuer ist ein ausdrücklich bestätigter Betrag mit Bruttokosten
als Obergrenze. Das Modell nimmt keine Steuerberechtigung an und leitet keinen
Vorsteuerbetrag aus pauschalen Kosten ab. Der vorhandene Vorsteuer-Schalter gilt
auch hier und ist keine Rechtsprüfung. Ausgangsumsatzsteuer wird auf den
vorsichtigen Bruttoverkaufserlös berechnet, **vor** Abzug der Verkaufsgebühren.

Einkaufskonstellationen `regular`, `no_vat_shown`, `margin_explicit`, `unknown`
werden getrennt von der Verkaufsbesteuerung dokumentiert. Kein USt-Ausweis und
explizite Differenzbesteuerung beim Einkauf begründen keine Berechtigung zur
Differenzbesteuerung beim Wiederverkauf. Unbekannter Einkauf und unbekannte oder
differenzbesteuerte Verkaufskonstellationen blockieren. Nicht ausgewiesene
Zuschlags-USt darf weder als positiver Steuersatz noch als abzugsfähige
Zuschlagsvorsteuer geplant werden; separat ausgewiesene Aufgeld-USt bleibt
getrennt. Die Rechnung muss die tatsächlichen Gebührenbasen bestätigen.

Die Bruttoverkaufsspanne gilt für das vollständige Los. Das konservative Szenario
verwendet die Untergrenze, reduziert um erwarteten Ausschuss und bestehenden
Sicherheitsabschlag. Obergrenze, Ausschussquote und Verkaufsdauer bleiben sichtbar.
Dies sind Planwerte, keine Marktpreisbelege. Entsorgung und Finanzierung werden
nicht automatisch aus Ausschuss oder Dauer erfunden. Die Dauer fließt nicht
nochmals als willkürlicher Score-Abschlag ein: notwendige Finanzierungskosten
müssen ausdrücklich geplant werden.

## Ergebnis und Maximalgebot

Maximalgebot ist das Minimum der Grenzen für Zielmarge, absoluten Zielgewinn und
verfügbares Bruttobudget. Der Liquiditätsbedarf berücksichtigt auch später
abziehbare Vorsteuer. Negative Gebotsobergrenzen werden auf null begrenzt;
`target_feasible=False` unterscheidet unerreichbare Ziele von einem zulässigen
Nullgebot. `current_bid_meets_targets` prüft das aktuelle Gebot gegen sämtliche
Grenzen. Verfügbare Liquidität darf nicht automatisch aus Vermögen abgeleitet
werden.

Der wirtschaftliche Score verwendet die vorhandene dokumentierte Heuristik auf
den konservativen Vollkostenwerten. Er ist kein nachgewiesener Handelsgewinn,
keine Rentabilitätswahrscheinlichkeit und keine autonome Kaufanweisung.
`technical_priority` misst unabhängig ausschließlich Finanzfeld-Vollständigkeit
(0–100); auch ein vollständiges Los kann steuerlich oder zeitlich gesperrt sein.
Standort/Transport sind über explizite Kosten enthalten. Attraktivität, Verkauf-
und Preisrisiko bleiben ohne Marktbelege menschliche Planungsannahmen.

## Verifikation

`python -m pytest tests/test_extended_economics.py -q`: 27 Tests bestanden.
Abgedeckt sind vollständige Zusatzkosten, Vermeidung doppelter bestehender Kosten,
Brutto-/Nettoumsatz, Gebühren außerhalb der Ausgangs-USt-Basis, Ausschuss und
Sicherheitsabschlag, Zielgewinn- und Margengrenze, Liquiditätsgrenze,
Vorsteuerbestätigung, Einkauf-/Verkauf-Steuergates, fehlende und ungültige Werte,
Dictionary-Schnittstelle und manuelle Prüfung. Testdaten sind synthetisch; daraus
folgt keine wirtschaftliche Validierung echter Möbelkäufe.
