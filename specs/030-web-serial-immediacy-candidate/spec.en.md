# Web-serial immediacy candidate

2026-08-28 · `SYSTEM-IMPROVE` · version-3 candidate; default behavior and quality claims remain unchanged.

Version 2 froze and generated six entirely fresh original tasks, but the author rejected all four texts in the first two reviewed pairs. The feedback identified literary posing, over-composed language, missing vividness and lived character presence, dialogue written in one polished model register, narrator-balanced claims that explained the scene, and insufficient web-serial atmosphere and plot pressure. The A/B mapping remains sealed. The remaining four pairs will not be presented, and unreviewed prose cannot fill in an evidence claim.

This evidence refutes any claim that version 2 improved the prose, but it does not establish a universal law of craft. It supports a narrower engineering diagnosis: concentrating on restraint, duplicated explanation and fragment control may produce tidier literary prose without producing web-fiction energy. The old pairwise harness also omitted the full Character Simulation and Reader Pressure path, so it was not an adequate proxy for the complete chapter quality the author wants to review.

## Version-3 candidate

Version 3 changes only the explicitly enabled `outline_driven` foundation and post-generation diagnostics:

- enter concrete present business soon enough for the reader to understand the want, resistance and actionable cost;
- advance through action, response and consequence, with each material response changing an option, judgment or cost;
- treat dialogue as a character's tactic for obtaining a result, shaped by listener, relationship, shared information, role and urgency;
- attach interiority to the object and next choice instead of letting the narrator turn the scene into a balanced proposition, maxim or thesis;
- prefer natural, concrete, speakable language without using ornament, pseudo-pace fragments, topical slang or fixed gratification beats as a proxy for serial voice;
- leave a traceable change in resource, information, relationship, position, commitment, risk or next task;
- stop Surface sentence work and return safe-but-flat prose to Reader Pressure, Scene or Plan.

These remain semantic objectives, not quotas for opening length, conflict count, dialogue length, sentence length, paragraph size or cliffhanger position. Formal scenes may be formal, reflective chapters may reflect, and everyday chapters need no invented danger. Genre, platform, project and current-request boundaries still determine applicability.

## Sequential one-chapter review

Future author review no longer uses A/B. Each iteration freezes one unseen complete-chapter task and exposes one chapter generated through the full production runtime and released by `candidate.visible.get`. Character Simulation and Reader Pressure must genuinely complete. Diagnostics, historical failures and rejected prose never enter Writer context.

The author records `continue | revise | reject | insufficient_evidence` with a concrete reason. No next task can be prepared before feedback is bound. After `revise` or `reject`, the same craft snapshot cannot retry under a different premise. `evals/craft_chapter_review.py` validates this sequence mechanically; all prose judgment remains with the author.

## Version, rollback and authority

The registry and foundation advance to version 3. The version-2 registry and bilingual foundation are preserved byte-for-byte under `surface/craft/history/v2/`; version-1 history remains intact. Existing runs continue to use their own frozen snapshots.

A new DRAFT still defaults to `baseline`. Only a new run explicitly using `craft_guidance_mode=outline_driven` receives version 3. A chapter observation, green tests or one `continue` response cannot change the default, activate durable taste, accept a manuscript or promote General Craft. This implementation also makes no automatic model call; the next chapter requires a separately authorized full production execution.
