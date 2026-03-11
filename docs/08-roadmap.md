# Roadmap - SpireMind STS2-first

## Fase 0 - Setup (1-2 giorni)

- struttura repository
- scaffolding moduli domain/engine/app/storage
- baseline test framework

Deliverable:

- progetto avviabile localmente
- documentazione MVP presente

## Fase 1 - Core decision engine (3-4 giorni)

- implementazione CardPickerEngine v1
- implementazione PathPlannerEngine v1
- implementazione EventAdvisorEngine v1
- explainability minima (2-4 reason strings)

Deliverable:

- suggerimenti affidabili su input manuale

## Fase 2 - UI e persistenza (2 giorni)

- Streamlit app con flusso run guidato
- salvataggio run/snapshot/decisioni su SQLite
- ripresa run interrotta

Deliverable:

- prodotto usabile durante run reale

## Fase 3 - Hardening (1-2 giorni)

- suite golden test iniziale
- tuning pesi su scenari benchmark
- miglioramento messaggi warning/errore

Deliverable:

- versione MVP stabile e pronta a uso continuo

## Fase 4 - Post-MVP (opzionale)

- supporto altri personaggi
- integrazione OCR assistita
- esportazione analytics run

## Milestone consigliata

Rilascio MVP interno entro 7-10 giorni lavorativi con focus su affidabilita, non feature breadth.
