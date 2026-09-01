# 语料文风三臂消融评测

这套评测要回答的是：在无指导基线和当前第五版写作方法之外，引入一份不含来源信息的语料候选指导，是否会改变实际阅读体验。它不负责生成正文，不自行判定文学赢家，也不会启用学习结果或授予发布权限。实现位于 [`style_corpus_ablation.py`](style_corpus_ablation.py)；仓库内的 [`fixtures/style_corpus_ablation_synthetic.json`](fixtures/style_corpus_ablation_synthetic.json) 只是一套明确标注为测试专用的原创合成材料。

## 冻结三臂条件

每个 case 只定义一份任务、一份上下文和一份随机性设置，而且三者都位于实验臂之上。评测器会分别计算三者的指纹，再计算整体生成绑定指纹。随后，三份外部提供的正文被绑定为：

- `baseline`：不注入写作方法的正文；
- `current_craft_v5`：使用当前冻结的第五版写作方法；
- `corpus_candidate`：使用一份去来源化的语料候选投影。

候选正文指纹直接取精确 UTF-8 字节的 SHA-256；写作方法指纹取完整绑定对象规范化 JSON 的 SHA-256。换行符、正文、writer projection、证据成员或任何已绑定字段发生变化，prepared plan 都会失效。

语料切分采用 leave-one-work-out，而不是随机抽几段正文。每个不透明 work ID 恰好留出一次；该折候选只能引用其余 work。每个 case 还会留出一个 scene function，该功能不能出现在候选的训练场景集合中。这些约束只证明实验条件分开了，不能证明文笔好坏。

## 匿名配对矩阵

三个实验臂会形成三个无序 pair。每个 case 的每个 pair 重复两轮；每轮都分别用正序和交换后的顺序呈现。因此，默认合成 suite 每个 case 会生成十二个 Blind Reader job。

独立语义合同为 `learning.blind_prose_pair`。它的 payload 只有：

- 不透明的 comparison ID；
- 三臂共享的任务和上下文；
- 三臂共享的 scene function；
- 匿名正文 `A` 与 `B`；
- 面向读者的判断标准。

实验臂名称、treatment 信息、语料来路、work ID、候选指纹、方法指纹、留出声明和预期答案在这个 payload 中都没有字段。真实的 `A`/`B` 映射只保存在指纹封闭的私有 plan 里。交换顺序时必须复用完全相同的两份正文；每个已完成的 review 还必须提供互不复用的独立调用谱系。

每个 completed review 会保留一条独立的 pair preference，可取 `a`、`b`、`tie`、`both_bad` 或 `insufficient_evidence`；同时必须完整返回八个分维记录。每个分维只有 leaning（`a`、`b`、`tie` 或 `unclear`）和一条不超过 800 字符的 observation：

- `content_fidelity`：是否遵守任务、冻结事实、视角和其他内容边界；
- `causal_movement`：动作、反应和信息是否改变下一步可能性；
- `target_mechanism`：case 指定的场景功能是否真正生效；
- `naturalness`：叙述、动作和对话是否自然，不显得被方法强行推动；
- `readability`：指代、空间、顺序、段落和信息负荷是否清楚；
- `engagement`：场景压力、好奇、情感牵引和继续阅读意愿；
- `diversity`：表达与结构是否有合乎语境的变化，而不是机械重复；
- `originality`：读感是否新鲜；它不代表与来源的距离，也不是泄漏放行结论。

pair preference 不会由这些分维计算出来。聚合层分别保留 preference 计数、各维计数、有界 observation 和交换顺序的一致性证据，不设置维度权重，不计算总分，也不选出赢家。

身材和外貌描写在这里属于普通正文证据。包括 `巨乳` 在内的具体身体词汇，不会自行改变已冻结的内容分区，也不会触发隔离或暗示标准答案。

## 独立的泄漏证据

泄漏评测不会混进 Blind Reader payload。第一步调用 [`../corpus/style_contract.py`](../corpus/style_contract.py) 的有界本地检查，记录精确重合、规范化重合、shingle 和 MinHash 结果，同时不返回命中的参考原文。本地结果无重合也仍然要求外部语义复核，不能把候选标记为可发布。

第二个独立语义合同是 `learning.prose_semantic_leakage`。它接收候选正文，以及带精确文本指纹的有界匿名参考片段，可以返回 `clear`、`blocked` 或 `insufficient_evidence`；findings 只能引用输入中已有的不透明 reference ID。常见类型元素、普通句法或单独出现的身体描写词都不足以证明泄漏。

语义泄漏是第九项独立证据，不是 Blind Reader 的第九个分维；它不能折算成 originality 分数，也不能合并到 pair preference 中。发布边界还注册了 `corpus.provenance.public_abstraction`：闭合输入只允许 completion、candidate、identity policy 和 provenance 指纹，声明的 rights class 与有界 basis，source dependency 是否仍然 current，以及 `public_general_style_atlas` 这一发布目标；没有标题、路径或正文字段。结果只能为 `pass`、`blocked` 或 `insufficient_evidence`，findings 有长度上限，且固定声明 `authority_scope=evidence_only`、`legal_safety_claim=false`。

本地检查和语义检查是两道不同的门。本地命中可以直接阻断泄漏路径；语义阻断或证据不足会单独保留。即便全部本地结果都干净、全部语义复核都为 clear，系统也只会记录“语义证据齐备”；`release`、`framework_promotion`、`canon_write` 和 `durable_user_taste_write` 仍然全部为 false。

## 结果状态与 API

prepare 阶段不会调用模型，初始状态始终是 `PENDING_MODEL`。缺失、失败或不支持的 review 继续保持 pending。完整的注册合同结果可以形成 `SEMANTIC_EVIDENCE_READY`、`LEAKAGE_BLOCKED` 或 `INCONCLUSIVE`，但证据对象不会给分维加权，不会生成文学质量总分，也不会自动选出赢家。若要给仓库内的合成 suite 注入 completed result，测试必须显式传入 `allow_synthetic=True`，最终状态也只能是 `SYNTHETIC_VALIDATION_ONLY`。

评测器提供以下公共接口：

- `load_suite` 与 `validate_suite`：读取并校验闭合 suite；
- `prepare_evaluation` 与 `validate_prepared`：构造和复核私有指纹 plan；
- `blind_reader_queue`：导出不含真实映射的匿名 pair jobs；
- `semantic_leakage_queue`：导出独立的语义泄漏 jobs；
- `consume_evidence`：校验独立结果并做无授权聚合。

[`../tests/test_quillframe_style_corpus_ablation.py`](../tests/test_quillframe_style_corpus_ablation.py) 只使用原创合成正文，覆盖确定性、精确绑定、留出隔离、payload 盲化、顺序平衡、独立调用谱系、泄漏状态组合、`body_appearance` 的普通处理，以及“不伪造模型结果”。这些测试通过，只能说明评测机械契约成立；真实读者在真实运行中更喜欢哪一臂，仍需实际独立证据。
