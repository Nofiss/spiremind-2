# Requisiti Funzionali - MVP STS2

## 1. Obiettivo funzionale

Il sistema deve suggerire decisioni durante una run di Slay the Spire 2, su tre domini:

- card reward
- pathing mappa
- eventi

## 2. Attori

- Utente principale: giocatore durante run live
- Sistema: motore raccomandazioni locale

## 3. Flusso utente principale

1. L'utente apre l'app e crea una nuova run
2. Inserisce/aggiorna lo stato run manualmente
3. Chiede un suggerimento (card/path/event)
4. Riceve ranking, motivazioni, confidenza e rischio
5. Salva la decisione e continua la run

## 4. Requisiti card pick

FR-CARD-001
Il sistema deve accettare tre opzioni carta (piu skip).

FR-CARD-002
Il sistema deve calcolare un punteggio per ogni opzione in base a:

- sinergia con deck corrente
- copertura bisogni (danno, difesa, scaling, aoe, draw, energia)
- stato HP e rischio prossimo tratto
- sinergia con relics presenti

FR-CARD-003
Il sistema deve restituire un ranking ordinato con motivazione testuale.

FR-CARD-004
Il sistema deve considerare l'opzione skip quando appropriato.

FR-CARD-005
Il sistema deve fornire confidenza (Low, Medium, High).

## 5. Requisiti pathing

FR-PATH-001
Il sistema deve accettare i nodi raggiungibili e i path candidati del tratto corrente.

FR-PATH-002
Il sistema deve valutare ogni path su:

- rischio danno/morte stimato
- valore atteso (elite, relic, shop, event)
- bisogno di rest/upgrade
- coerenza col deck plan corrente

FR-PATH-003
Il sistema deve restituire 1-3 percorsi consigliati con ranking.

FR-PATH-004
Per ogni path deve fornire una spiegazione sintetica e una nota di rischio.

## 6. Requisiti eventi

FR-EVT-001
Il sistema deve accettare nome evento e opzioni disponibili.

FR-EVT-002
Per ogni opzione deve stimare impatto su:

- hp immediato
- valore deck
- economia (gold/rimozioni)
- potenza attesa per i prossimi fight

FR-EVT-003
Il sistema deve raccomandare una scelta con fallback conservativo se info parziali.

## 7. Gestione stato run

FR-STATE-001
Il sistema deve mantenere stato run coerente per tutta la sessione.

FR-STATE-002
Il sistema deve permettere aggiornamenti incrementali (dopo ogni stanza).

FR-STATE-003
Il sistema deve validare input e segnalare campi mancanti/bloccanti.

FR-STATE-004
Il sistema deve mantenere storico delle decisioni nella run.

## 8. Explainability e UX

FR-UX-001
Ogni suggerimento deve includere almeno 2 motivazioni leggibili.

FR-UX-002
Ogni suggerimento deve esplicitare livello di confidenza.

FR-UX-003
L'interfaccia deve minimizzare i campi necessari per domanda rapida in run.

## 9. Persistenza

FR-DATA-001
Il sistema deve salvare run, snapshot stato e decisioni in locale.

FR-DATA-002
Il sistema deve permettere ripresa run interrotta.

## 10. Criteri di accettazione MVP

- Card pick funzionante su casi comuni Atto 1-2 STS2
- Pathing con ranking consistente su path candidati
- Event advisor attivo su eventi piu frequenti e fallback sugli altri
- Nessun blocco su input validi
- Spiegazioni presenti in ogni output
