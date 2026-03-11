# Requisiti Tecnici - MVP STS2

## 1. Vincoli di progetto

- Time-to-market breve con affidabilita alta
- Esecuzione locale offline-first
- Comportamento deterministico e testabile

## 2. Stack tecnologico

- Linguaggio: Python 3.11+
- UI: Streamlit
- Core engine: librerie Python modulari (no dipendenza UI)
- Persistenza: SQLite
- Testing: pytest
- Packaging: requirements.txt e script run locale

## 3. Architettura software

Il sistema deve essere separato in moduli:

- domain: modelli run e validazioni
- engine: scoring card/path/event
- explain: generazione motivazioni
- app: interfaccia e orchestrazione
- storage: accesso dati locale

## 4. Performance

NFR-PERF-001
Tempo risposta suggerimento < 300 ms su hardware desktop medio (escluso tempo input utente).

NFR-PERF-002
Tempo avvio applicazione < 5 secondi in ambiente locale standard.

## 5. Affidabilita e robustezza

NFR-REL-001
Nessun crash su input validi.

NFR-REL-002
Validazione con errori espliciti su input invalidi/incompleti.

NFR-REL-003
Fallback conservativo quando mancano dati non bloccanti.

NFR-REL-004
A parita di input, output identico (determinismo).

## 6. Qualita codice

- Tipizzazione Python su moduli core
- Regole lint e format coerenti
- Copertura test orientata alle decisioni core

Target iniziali:

- >= 80% coverage su engine e domain
- >= 90% coverage su funzioni critiche di scoring

## 7. Test strategy

Test richiesti:

- unit test su scoring parziale per feature (danno, block, scaling)
- unit test su validazioni RunState
- integration test su flusso "input -> raccomandazione"
- golden test su scenari predefiniti STS2

## 8. Logging e osservabilita

- Log locale strutturato (json lines o formato chiaro)
- Eventi minimi: richiesta, score top-3, scelta finale, confidenza, tempo risposta
- Tracciamento errori con contesto input ridotto (senza dati sensibili)

## 9. Sicurezza e privacy

- Nessun invio dati obbligatorio verso servizi esterni
- Dati run solo locali per default
- Nessun segreto richiesto per utilizzo base

## 10. Estendibilita

Il design deve consentire:

- aggiunta nuovi personaggi tramite config e pesi dedicati
- sostituzione futura del motore euristico con modello ibrido
- aggiunta modulo OCR senza rompere API interne

## 11. Definition of Done tecnica (MVP)

- Applicazione avviabile localmente con comando unico
- Tutti i test core verdi in CI locale
- Documentazione minima architettura e requisiti presente
- Demo end-to-end su una run STS2 possibile
