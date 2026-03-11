# Recommendation Engine - MVP STS2

## 1. Principi del motore

- deterministico
- spiegabile
- robusto a input parziale
- ottimizzato per decisioni rapide in run

## 2. Strategia di scoring

Ogni opzione riceve score da somma pesata di feature.

Formula concettuale:

score_total = base_value + synergy_score + need_coverage + risk_adjustment + future_value

Score clamp nel range 0-100.

## 3. Card picker

Feature principali:

- deck synergy (tag match)
- immediate survival value (hp basso => peso block)
- prossimo tratto (elite/fight denso => priorita frontload/aoe)
- curva energia e costo medio deck
- confronto con opzione skip

Output:

- ranking opzioni
- rationale (2-4 motivi)
- confidence

Regola skip:

- se tutte le carte hanno score sotto soglia minima e deck e gia coerente

## 4. Path planner

Ogni path candidato viene valutato su due assi:

- Value Axis: elite potential, shop utility, event value, upgrade opportunities
- Risk Axis: expected hp loss, death risk, resource strain

Score path:

path_score = value_axis - risk_penalty + deck_plan_fit

Esempi di bias contestuale:

- HP basso + pochi rest: penalizza path aggressivi
- deck forte ma non scalante per boss: premia upgrade/value path
- gold alto + deck sporco: aumenta valore shop/removal

## 5. Event advisor

Per evento noto, opzioni valutate con template di impatto:

- hp delta
- deck quality delta
- economy delta
- tempo di payoff (immediato vs futuro)

Per evento non noto:

- fallback su euristica conservativa basata su costo HP e valore certo

## 6. Confidence model

Confidence dipende da:

- margine score tra prima e seconda opzione
- completezza input
- copertura regola (evento noto vs generico)

Soglie indicative:

- High: margine elevato + input completo
- Medium: margine medio o lieve incertezza
- Low: opzioni vicine o dati incompleti

## 7. Explainability

Le spiegazioni vengono generate da feature contributive top-N.

Formato consigliato:

- "Perche ora"
- "Sinergia con il deck"
- "Rischio associato"

## 8. Configurazione e tuning

- pesi in file configurabile versionato
- tuning manuale iniziale con scenari benchmark
- no auto-learning nel MVP

## 9. Fail-safe

Se stato incompleto:

- warning esplicito
- riduzione confidence
- suggerimento conservativo con motivazione
