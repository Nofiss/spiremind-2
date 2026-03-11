# Architettura - MVP STS2

## 1. Visione architetturale

Architettura modulare monolitica locale.
L'obiettivo e separare chiaramente logica di dominio, motore decisionale e UI.

## 2. Componenti principali

- UI Layer (Streamlit)
  - form input stato run
  - viste suggerimenti card/path/event
  - storico decisioni run

- Application Service
  - orchestration use case
  - validazione richieste
  - chiamata motori e composizione risposta

- Domain Layer
  - modelli RunState, CardOption, PathOption, EventOption
  - enum e regole di coerenza

- Recommendation Engine
  - CardPickerEngine
  - PathPlannerEngine
  - EventAdvisorEngine

- Explanation Engine
  - trasforma score features in motivazioni testuali concise

- Storage Layer
  - repository SQLite per run/snapshot/decisioni

## 3. Flusso dati high-level

1. Utente aggiorna stato run
2. Application Service valida e normalizza
3. Engine calcola score componenti
4. Explanation Engine genera reason strings
5. Risposta composta con ranking, confidence, rischio
6. Storage salva snapshot e decisione

## 4. Contratti interni (concettuali)

request -> engine -> response

CardRecommendationRequest:

- run_state
- card_options (3 + skip)

CardRecommendationResponse:

- ranked_options[]
- confidence
- risk_note

Contratti analoghi per Path e Event.

## 5. Decisioni architetturali chiave

ADR-001
Input manuale nel MVP per ridurre complessita e aumentare affidabilita.

ADR-002
Motore deterministic rule-based prima di ML per prevedibilita e debug.

ADR-003
UI e core disaccoppiati per migrare in futuro a API/FastAPI senza riscrivere engine.

## 6. Error handling

- Errori validazione: messaggi user-friendly con campo coinvolto
- Errori runtime engine: fallback con raccomandazione conservativa
- Errori storage: warning non bloccante se possibile

## 7. Scalabilita futura

Percorso evolutivo previsto:

- aggiunta character profiles (Silent/Defect/Watcher)
- introduzione OCR adapter come nuovo input provider
- migrazione opzionale a servizio API mantenendo engine invariato
