# Implementation plan

1. Extend typed book planning with the story foundation, character arcs and relationship arcs while keeping these artifacts outside settled story-state tables.
2. Split the chapter payload into a chapter contract and scene script, and add causal state-change fields to each scene.
3. Cut plan and WriterPack schemas to their new exact versions and register Project schema fragment 024 as a fail-closed state marker.
4. Derive WriterPack scene briefs from the frozen scene script, preserving the existing four-layer fingerprint inheritance as the only source.
5. Update the Bridge fixtures and Studio plan serializer to emit the new exact payload.
6. Add deterministic structural, fingerprint, restart and end-to-end production tests; run the Rust workspace quality gates without live model calls.

