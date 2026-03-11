# Domain Model - MVP STS2

## 1. Entita principali

RunState

- run_id: string
- game_id: "STS2"
- character: "IRONCLAD"
- ascension: int (0-20)
- act: int (1-3+)
- floor: int
- current_hp: int
- max_hp: int
- gold: int
- deck_summary: DeckSummary
- relics: list[RelicId]
- potions: list[PotionId]
- map_context: MapContext
- recent_decisions: list[DecisionRecord]

DeckSummary

- total_cards: int
- attack_count: int
- skill_count: int
- power_count: int
- tags: DeckTags

DeckTags

- block_density: float
- frontload_damage: float
- scaling_damage: float
- aoe_coverage: float
- draw_quality: float
- energy_flex: float
- exhaust_synergy: float
- strength_synergy: float

MapContext

- reachable_paths: list[PathCandidate]
- next_elite_possible: bool
- rest_sites_available: int
- shops_available: int
- events_available: int

DecisionRecord

- decision_type: CARD|PATH|EVENT
- options: serialized
- recommended: string
- accepted_by_user: bool|null
- timestamp: datetime

## 2. Input models per use case

CardPickInput

- run_state
- options: [card_a, card_b, card_c, skip]

PathInput

- run_state
- candidate_paths (precalcolati da UI o inseriti manualmente)

EventInput

- run_state
- event_name
- options

## 3. Output models per use case

RecommendationOption

- id
- score_total (0-100)
- confidence_component
- reasons[2..4]
- risk_level (LOW|MEDIUM|HIGH)

RecommendationResult

- top_choice
- ranked_options
- overall_confidence (LOW|MEDIUM|HIGH)
- caution_note

## 4. Invarianti dominio

- game_id deve essere STS2 nel MVP
- character deve essere IRONCLAD nel MVP
- 0 <= current_hp <= max_hp
- floor >= 0
- act >= 1
- card pick con esattamente 3 opzioni + skip
- score normalizzato sempre nel range 0-100

## 5. Taxonomy iniziale tag deck (STS2 generic)

Tag principali:

- block_core
- strength_scaling
- exhaust_engine
- status_payoff
- aoe_plan
- boss_burst

Questi tag guidano scoring e spiegazioni, non sostituiscono il dettaglio carta per carta.
