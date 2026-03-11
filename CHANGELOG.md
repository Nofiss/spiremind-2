# Changelog

## v0.1.0 - STS2 MVP (Ironclad)

Data: 2026-03-11

### Added

- MVP STS2-only con personaggio Ironclad
- Card picker, path planner, event advisor con explainability
- Discovery progressiva entita (known/discovered/reviewed)
- Knowledge Review UI per completare il catalogo nel tempo
- KPI dashboard locale con p95 latency, low confidence %, reviewed %
- Bootstrap centralizzato (`spiremind/bootstrap.py`)
- Schema versioning base e migrazione minima
- Golden tests e test di regressione su flussi principali

### Changed

- Rimosso bias contenuti STS1 e introdotto micro-seed STS2
- Rafforzata policy fallback unknown per ridurre rischio decisionale
- Tuning iniziale del path planner in funzione di HP e gold

### Quality

- Test suite aggiornata e verde
- Output deterministico per input uguali
