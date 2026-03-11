# SpireMind MVP (Python, STS2)

Assistente decisionale per Slay the Spire 2, orientato a run STS2 con supporto discovery-first.

Funzionalita MVP:

- suggerimento scelta carta (ranking + confidence + motivazioni)
- suggerimento percorso (ranking rischio/valore)
- suggerimento eventi (known + fallback conservativo)
- discovery progressiva di carte/eventi sconosciuti
- coda review per entita scoperte (discovered -> reviewed)

## Requisiti

- Python 3.11+

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Avvio app

```bash
streamlit run app.py
```

## Test

```bash
pytest
```

## Bootstrap locale

L'app inizializza automaticamente il database locale (`spiremind.db`) con micro-seed STS2 al primo avvio.
Per avviare il bootstrap manualmente da Python:

```bash
python -c "from spiremind.bootstrap import bootstrap; bootstrap('spiremind.db')"
```

## Note architetturali

- package core: `spiremind/`
- UI: `app.py`
- documentazione: `docs/`

## Release notes

- changelog: `CHANGELOG.md`
