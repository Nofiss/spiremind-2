# Product Vision - SpireMind MVP

## Obiettivo

SpireMind e un assistente decisionale per run di Slay the Spire 2.
Nel MVP il prodotto supporta un solo personaggio (Ironclad) e aiuta il giocatore in tre momenti:

- scelta carta dopo il combattimento
- scelta percorso sulla mappa
- scelta opzione evento

L'obiettivo e ridurre errori decisionali, aumentare coerenza della strategia e mantenere tempi di decisione brevi.

## Problema

Durante una run, il giocatore prende molte decisioni ad alta varianza con informazioni incomplete.
Errori piccoli nelle prime stanze (card pick o pathing) possono degradare tutto l'atto successivo.

Problemi principali:

- difficile valutare trade-off tra valore immediato e valore futuro
- difficile adattare il deck plan ai nemici probabili del prossimo tratto
- eventi con outcome non banali da valutare sotto pressione

## Utente target

- Giocatore che vuole migliorare win rate e consistenza
- Esperienza da principiante avanzato a intermedio
- Utilizzo durante la run, non solo analisi post-run

## Value proposition

SpireMind fornisce suggerimenti pratici e spiegati, non solo un output "best pick".

Ogni raccomandazione include:

- ranking opzioni
- motivazioni leggibili
- livello di confidenza
- nota di rischio

## Scope MVP

Incluso nel MVP:

- solo STS2 con personaggio Ironclad
- input manuale stato run
- motore deterministico regole + scoring euristico
- UI locale semplice e veloce
- persistenza storico locale

Fuori scope MVP:

- OCR realtime dello schermo
- supporto Silent/Defect/Watcher
- training ML online
- integrazione cloud obbligatoria

## Criteri di successo MVP

- prodotto utilizzabile in run reali senza blocchi
- latenza media suggerimento < 300 ms (input gia inserito)
- output con spiegazioni consistenti per almeno il 95% dei casi validi
- percezione di utilita >= 4/5 in test utente interno
