# Execution Plan - SpireMind STS2 (Ironclad)

## Obiettivo

Portare il MVP STS2 a uno stato "usabile e affidabile" in run reali, con tracciamento chiaro delle attivita e progressi.

## Stato attuale (baseline)

- STS2-only con personaggio Ironclad
- Discovery workflow: known/discovered/reviewed
- UI Streamlit con tab Knowledge Review
- Test suite attuale: pass

## Sprint Plan (5 giorni)

### Day 1 - Hygiene + Bootstrap

- [x] Aggiungere `.gitignore` (db locale, venv, cache Python, pytest cache)
- [x] Consolidare bootstrap DB/seed in funzione dedicata
- [x] Verificare setup da zero su ambiente pulito

DoD:

- repo pulito
- bootstrap idempotente
- test verdi

### Day 2 - Schema Stability + Catalog Safety

- [x] Introdurre `schema_version` DB
- [x] Migrazione minima compatibile (se schema cambia)
- [x] Rendere seed/discovery robusti contro duplicati

DoD:

- riavvii multipli senza side effects
- nessun duplicato non voluto in catalogo

### Day 3 - Golden Tests STS2

- [x] Creare scenari benchmark card/path/event (known + unknown-heavy)
- [x] Definire expected top-choice/ranking per ogni scenario
- [x] Integrare golden test in suite

DoD:

- baseline decisionale congelata
- regressioni rilevabili automaticamente

### Day 4 - Engine Tuning

- [x] Tarare pesi CardPicker (survival/value/scaling)
- [x] Migliorare PathPlanner su HP basso/rischio cumulativo
- [x] Rafforzare fallback unknown + confidence policy

DoD:

- miglior coerenza su scenari benchmark
- niente regressioni golden

### Day 5 - Knowledge Workflow + KPI

- [x] Ordinare review queue per `times_seen`
- [x] Aggiungere filtri review (solo discovered / piu frequenti)
- [x] Esporre KPI locali minimi
  - p95 latency
  - % confidence LOW
  - % reviewed

DoD:

- review piu rapida
- metriche osservabili e utili per iterazioni

## KPI target MVP

- p95 latency suggerimento: < 300ms (input manuale)
- crash-free rate: ~100% su input validi
- % confidence LOW in calo nel tempo
- % entita reviewed in crescita run dopo run

## Rischi principali e mitigazioni

- Molte entita unknown all'inizio
  - Mitigazione: review queue prioritaria + micro-seed + fallback conservativo
- Regressioni durante tuning
  - Mitigazione: golden tests obbligatori prima/dopo tuning
- Drift qualita suggerimenti
  - Mitigazione: KPI locali + benchmark fissi

## Regole operative

- Nessun merge senza test verdi
- Ogni modifica scoring deve aggiornare changelog tuning
- Ogni nuovo comportamento deve avere almeno 1 test dedicato
