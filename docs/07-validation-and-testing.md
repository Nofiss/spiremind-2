# Validation and Testing - MVP STS2

## 1. Obiettivi quality

- assicurare stabilita su run reali
- garantire output coerenti e spiegabili
- prevenire regressioni nel tuning pesi

## 2. Tipi di test

### 2.1 Unit test

Copertura minima:

- scoring feature-level (card/path/event)
- validazione invarianti RunState
- normalizzazione e clamp score

### 2.2 Integration test

Flussi principali:

- update stato -> richiesta suggerimento -> risposta completa
- persistenza snapshot + decisione
- ripresa run salvata

### 2.3 Golden tests

Dataset di scenari noti STS2, con expected ranking o expected top-choice.
Ogni cambiamento di pesi o regole deve passare la suite golden.

### 2.4 Smoke test UI

- avvio app
- compilazione input minimo
- visualizzazione output card/path/event

## 3. Piano scenari benchmark

Set iniziale consigliato:

- Atto 1 early con deck base
- Atto 1 pre-elite a HP medio
- Atto 2 con scaling incompleto
- situazione HP critico con path aggressivo disponibile
- evento trade-off HP vs power

## 4. Metriche di validazione

Metriche tecniche:

- p95 latency suggerimento
- crash-free session rate
- numero warning validazione per run

Metriche prodotto:

- accettazione suggerimento da parte utente
- rating utilita spiegazioni (1-5)
- tempo decisione medio

## 5. Criteri go-live MVP

- test suite core 100% green
- golden tests senza regressioni critiche
- latenza p95 entro target
- nessun bug bloccante noto nei flussi principali

## 6. Strategia regressione

- ogni modifica engine richiede run test completa
- aggiornamento golden snapshots solo con motivazione esplicita
- changelog decisionale per modifiche pesi
