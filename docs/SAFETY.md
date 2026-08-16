# Safety and legal boundary

BasedDoor is a local automation and evidence-assistance project. It is not a lawyer, emergency service, police detector, warrant validator, or substitute for professional advice.

## Product invariants

- **No fabricated recording state.** A camera entity does not mean recording is active.
- **No identity assertion from vision.** A model may classify visible clothing/features, but BasedDoor must not present that as proof of occupation or authority.
- **No legal-validity verdicts.** Document AI may extract visible text and flag unreadable or ambiguous fields for human review; it must not pronounce a document valid or invalid.
- **No obstruction logic.** BasedDoor does not tell a user to physically interfere with a person acting under lawful authority or in an emergency.
- **No hidden cloud fallback.** If a local dependency fails, the system degrades to a local deterministic response.
- **Evidence and interpretation stay separate.** Original images/logs should be retained separately from OCR, summaries, classifications, and other derived output.

## Canada

Canadian search powers and warrant requirements depend on the authority and circumstances. Criminal Code s. 487 contains a general search-warrant process. Section 487.11 permits specified warrantless powers where the conditions for obtaining a warrant exist but exigent circumstances make obtaining one impracticable. Section 487.093 sets duties for people executing certain warrants, including providing or affixing a copy and notice in specified circumstances.

Because facts and legal authority matter, BasedDoor should communicate only the resident's configured response, avoid providing consent through the system, and preserve information. It should not decide whether an officer may act.

Always verify current law from official federal or provincial sources and consult a qualified lawyer for legal advice.
