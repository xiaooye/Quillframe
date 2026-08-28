# Chinese webnovel research and adoption

Status: implementation research, not a reader-retention result. Repository observations are pinned in [the research register](research-register.yaml); no external skill was installed or external code imported. Popularity is a discovery signal, not a quality score.

## Decisions that affect this implementation

| Source | Useful mechanism | Quillframe boundary |
| --- | --- | --- |
| [webnovel-writer](https://github.com/lingfengQAQ/webnovel-writer/tree/2041abad78211e29a67a2f0c64b2a97a747dce57) | Stage ledger and chapter-state projections | Exact candidate review, explicit author acceptance and atomic settlement remain separate. GPL code was not copied. |
| [chinese-novelist-skill](https://github.com/PenglongHuang/chinese-novelist-skill/tree/3db1e3be88343ca531924b0dc6516710f1b11779) | Progressive questions about genre and voice | Use a short editable Plan intake. No unattended whole-book acceptance; no license was found at the inspected revision. |
| [ani-book-skill](https://github.com/ExplosiveCoderflome/ani-book-skill/tree/44a0eb216eee234101af1984df20726713b7690e) | Goal, resistance, reward, net change and rolling plans | Optional reader-intent fields; a quiet chapter may still deliver value. Named roles in one engine are not independent review. |
| [chinese-webnovel-skills](https://github.com/tance-mang/chinese-webnovel-skills/tree/ecf552f6930e769d8bbf17818ad3d5a864a7a70b) | Modular writing guidance and reader predictions | Load relevant guidance only. Model reactions are advisory, never real audience measurements. |
| [webnovel-handbook](https://github.com/miserylee/webnovel-handbook/tree/700b2a718c9d3c79f946b35abc7b037088532bac) | Feedback and memory workflows | Keep author, human-reader and model sources distinct; project preferences need review and explicit activation. |
| [novel-architect](https://github.com/zhougz520/novel-architect/tree/8be80352257f98151921d89200e63464759a329f) | Reader promise records | Bind expectations to accepted source chapters. Keyword pressure counts cannot establish engagement. |

## Corrected paper attributions

[Learning to Reason for Long-Form Story Generation](https://arxiv.org/abs/2503.22828) studies next-chapter prediction and reinforcement learning, not character simulation. This implementation does not train weights.

[From Personas to Plot](https://arxiv.org/abs/2607.00918) presents MAGNET character-driven actions and ATLAS scene/world graphs. It informs causal scene state, not a claim that an arbitrary critique loop improves reader retention.

[ConWriter](https://arxiv.org/abs/2608.05169) uses evolving state, transition checks and localized repair. [Lost in Stories](https://aclanthology.org/2026.findings-acl.410/) contributes ConStory-Bench and contradiction checking. These support source-bound continuity evidence, not a universal literary score.

[Agents' Room](https://proceedings.iclr.cc/paper_files/paper/2025/file/0fbc8a83d93dd8021a4dd8d2d34138eb-Paper-Conference.pdf) separates planning and writing through a shared scratchpad. Its short-story experiments do not prove serial-book scale. Quillframe also keeps future plans and private character state out of blind-reader packets.

## What remains to be measured

The product goal is reader engagement: worthwhile questions, attachment to characters, meaningful choices, perceptible payoff and a reason to continue. A model judgment is a diagnostic prediction. Human reading and explicit author decisions remain distinct evidence.

Use four development cases and six held-out cases. Cap every experiment round at 64 actual calls including context selection, critics and repair. Record incomplete rounds honestly. The single-chapter, three-chapter and twelve-chapter chain requires author confirmation between chapters; deterministic tests and created chapter rows do not satisfy it. No market-retention or million-word-consistency claim is made.
