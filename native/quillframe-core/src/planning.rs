use std::collections::{BTreeMap, HashMap};

use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::{fingerprint::sha256_fingerprint, CoreError, CoreResult, StoryGraph, StoryKind};

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "SCREAMING-KEBAB-CASE")]
pub enum PlanMode {
    DesignBook,
    DesignVolume,
    PlanUnit,
    PlanChapter,
}

impl PlanMode {
    pub fn target_kind(self) -> StoryKind {
        match self {
            Self::DesignBook => StoryKind::Book,
            Self::DesignVolume => StoryKind::Volume,
            Self::PlanUnit => StoryKind::Unit,
            Self::PlanChapter => StoryKind::Chapter,
        }
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct PlanTarget {
    pub reference: String,
    pub node_id: String,
    pub kind: StoryKind,
}

impl PlanTarget {
    pub fn resolve(graph: &StoryGraph, mode: PlanMode, node_id: &str) -> CoreResult<Self> {
        let node = graph
            .node(node_id)
            .ok_or_else(|| CoreError::InvalidPlan("plan target does not exist".into()))?;
        if node.kind != mode.target_kind() {
            return Err(CoreError::InvalidPlan(
                "plan mode does not match target kind".into(),
            ));
        }
        Ok(Self {
            reference: graph.canonical_target(node_id)?,
            node_id: node_id.to_owned(),
            kind: node.kind,
        })
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ReaderContract {
    pub reader_question: String,
    pub visible_reward: String,
    pub character_choice: String,
    pub cost: String,
    pub net_change: String,
    pub next_pull: String,
}

impl ReaderContract {
    fn validate(&self) -> CoreResult<()> {
        for (field, value) in [
            ("reader_question", &self.reader_question),
            ("visible_reward", &self.visible_reward),
            ("character_choice", &self.character_choice),
            ("cost", &self.cost),
            ("net_change", &self.net_change),
            ("next_pull", &self.next_pull),
        ] {
            if value.trim().is_empty() {
                return Err(CoreError::InvalidPlan(format!("{field} must be non-empty")));
            }
        }
        Ok(())
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct BookPlan {
    pub reader_promise: String,
    pub protagonist_agency: String,
    pub central_conflict: String,
    pub progression: Vec<String>,
    pub endgame_reserve: Vec<String>,
    pub anti_exhaustion_limits: Vec<String>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct VolumePlan {
    pub volume_promise: String,
    pub net_situation_change: String,
    pub opposition: String,
    pub relationship_movements: Vec<String>,
    pub climax: String,
    pub inherited_debts: Vec<String>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct UnitPlan {
    pub loop_question: String,
    pub setup: Vec<String>,
    pub release: String,
    pub aftermath: String,
    pub rewards: Vec<String>,
    pub delay_costs: Vec<String>,
    pub foreshadowing: Vec<String>,
    pub callbacks: Vec<String>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SceneObjective {
    pub scene_id: String,
    pub ordinal: u32,
    pub viewpoint: String,
    pub location: String,
    pub entry_state: String,
    pub objective: String,
    pub opposition: String,
    pub turn: String,
    pub exit_state: String,
    pub emotion_target: String,
    pub reader_effect: String,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum LengthUnit {
    ChineseCharacters,
    Words,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct LengthBand {
    pub min: u32,
    pub max: u32,
    pub unit: LengthUnit,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ConstraintClause {
    pub id: String,
    pub statement: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ChapterConstraintLock {
    pub length: LengthBand,
    pub must_happen: Vec<ConstraintClause>,
    pub must_not_happen: Vec<ConstraintClause>,
    pub exact_time_anchors: Vec<ConstraintClause>,
    pub stop_point: String,
    pub end_debt: String,
}

impl ChapterConstraintLock {
    fn validate(&self, reader_contract: &ReaderContract) -> CoreResult<()> {
        if self.length.min == 0 || self.length.min > self.length.max {
            return Err(CoreError::InvalidPlan(
                "chapter length band must be positive and ordered".into(),
            ));
        }
        require_texts([&self.stop_point, &self.end_debt])?;
        if self.end_debt != reader_contract.next_pull {
            return Err(CoreError::InvalidPlan(
                "chapter end debt must equal the reader contract next pull".into(),
            ));
        }
        let mut ids = std::collections::BTreeSet::new();
        for clause in self
            .must_happen
            .iter()
            .chain(&self.must_not_happen)
            .chain(&self.exact_time_anchors)
        {
            require_texts([&clause.id, &clause.statement])?;
            if !ids.insert(clause.id.clone()) {
                return Err(CoreError::InvalidPlan(
                    "chapter constraint clause ids must be unique".into(),
                ));
            }
        }
        Ok(())
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ChapterPlan {
    pub reader_contract: ReaderContract,
    pub constraint_lock: ChapterConstraintLock,
    pub scenes: Vec<SceneObjective>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(tag = "kind", content = "body", rename_all = "snake_case")]
pub enum PlanBody {
    Book(BookPlan),
    Volume(VolumePlan),
    Unit(UnitPlan),
    Chapter(ChapterPlan),
}

impl PlanBody {
    pub(crate) fn kind(&self) -> StoryKind {
        match self {
            Self::Book(_) => StoryKind::Book,
            Self::Volume(_) => StoryKind::Volume,
            Self::Unit(_) => StoryKind::Unit,
            Self::Chapter(_) => StoryKind::Chapter,
        }
    }

    fn validate(&self) -> CoreResult<()> {
        match self {
            Self::Book(value) => require_texts([
                &value.reader_promise,
                &value.protagonist_agency,
                &value.central_conflict,
            ]),
            Self::Volume(value) => require_texts([
                &value.volume_promise,
                &value.net_situation_change,
                &value.opposition,
                &value.climax,
            ]),
            Self::Unit(value) => {
                require_texts([&value.loop_question, &value.release, &value.aftermath])
            }
            Self::Chapter(value) => {
                value.reader_contract.validate()?;
                value.constraint_lock.validate(&value.reader_contract)?;
                if value.scenes.is_empty() {
                    return Err(CoreError::InvalidPlan(
                        "chapter plan requires at least one scene objective".into(),
                    ));
                }
                let mut expected = 1;
                for scene in &value.scenes {
                    if scene.ordinal != expected {
                        return Err(CoreError::InvalidPlan(
                            "scene objectives must use contiguous ordinals".into(),
                        ));
                    }
                    require_texts([
                        &scene.scene_id,
                        &scene.viewpoint,
                        &scene.location,
                        &scene.entry_state,
                        &scene.objective,
                        &scene.opposition,
                        &scene.turn,
                        &scene.exit_state,
                        &scene.emotion_target,
                        &scene.reader_effect,
                    ])?;
                    expected += 1;
                }
                Ok(())
            }
        }
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct FrozenPlanLayer {
    pub target: PlanTarget,
    pub proposal_id: Uuid,
    pub active_version: u64,
    pub proposal_fingerprint: String,
    pub body: PlanBody,
}

impl FrozenPlanLayer {
    pub fn from_active(proposal: &PlanProposal, active_version: u64) -> CoreResult<Self> {
        proposal.validate_fingerprint()?;
        let value = Self {
            target: proposal.target.clone(),
            proposal_id: proposal.id,
            active_version,
            proposal_fingerprint: proposal.fingerprint.clone(),
            body: proposal.body.clone(),
        };
        value.validate()?;
        Ok(value)
    }

    fn validate(&self) -> CoreResult<()> {
        if self.active_version == 0
            || self.target.kind != self.body.kind()
            || !is_fingerprint(&self.proposal_fingerprint)
            || self.target.reference.trim().is_empty()
            || self.target.node_id.trim().is_empty()
        {
            return Err(CoreError::InvalidPlan(
                "frozen plan layer is incomplete or mismatched".into(),
            ));
        }
        self.body.validate()
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct HierarchicalPlanLock {
    pub schema: String,
    pub layers: Vec<FrozenPlanLayer>,
    pub fingerprint: String,
}

impl HierarchicalPlanLock {
    pub fn freeze(layers: Vec<FrozenPlanLayer>) -> CoreResult<Self> {
        let mut value = Self {
            schema: "quillframe_hierarchical_plan_lock_v1".into(),
            layers,
            fingerprint: String::new(),
        };
        value.validate_fields()?;
        value.fingerprint = value.compute_fingerprint()?;
        Ok(value)
    }

    pub fn validate(&self) -> CoreResult<()> {
        self.validate_fields()?;
        if self.fingerprint != self.compute_fingerprint()? {
            return Err(CoreError::AuthorityConflict(
                "hierarchical plan lock fingerprint changed".into(),
            ));
        }
        Ok(())
    }

    pub fn chapter_plan(&self, chapter_id: &str) -> CoreResult<&ChapterPlan> {
        self.validate()?;
        let layer = self.layers.last().ok_or_else(|| {
            CoreError::InvalidPlan("hierarchical plan lock has no chapter layer".into())
        })?;
        if layer.target.node_id != chapter_id {
            return Err(CoreError::InvalidPlan(
                "hierarchical plan lock targets a different chapter".into(),
            ));
        }
        match &layer.body {
            PlanBody::Chapter(plan) => Ok(plan),
            _ => Err(CoreError::InvalidPlan(
                "hierarchical plan lock ends with a non-chapter body".into(),
            )),
        }
    }

    fn validate_fields(&self) -> CoreResult<()> {
        if self.schema != "quillframe_hierarchical_plan_lock_v1" || self.layers.len() != 4 {
            return Err(CoreError::InvalidPlan(
                "hierarchical plan lock requires exactly book, volume, unit and chapter".into(),
            ));
        }
        let expected = [
            StoryKind::Book,
            StoryKind::Volume,
            StoryKind::Unit,
            StoryKind::Chapter,
        ];
        for (index, layer) in self.layers.iter().enumerate() {
            layer.validate()?;
            if layer.target.kind != expected[index] {
                return Err(CoreError::InvalidPlan(
                    "hierarchical plan lock layers are missing or out of order".into(),
                ));
            }
            if index > 0 {
                let expected_dependency = &self.layers[index - 1];
                // Exact lineage is checked by the data layer; here we prevent repeated or
                // self-referential typed targets without pretending to infer story semantics.
                if layer.target.node_id == expected_dependency.target.node_id {
                    return Err(CoreError::InvalidPlan(
                        "hierarchical plan lock repeats a target".into(),
                    ));
                }
            }
        }
        Ok(())
    }

    fn compute_fingerprint(&self) -> CoreResult<String> {
        let mut projection = self.clone();
        projection.fingerprint.clear();
        let bytes = serde_json::to_vec(&projection)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        Ok(sha256_fingerprint(bytes))
    }
}

fn require_texts<'a>(values: impl IntoIterator<Item = &'a String>) -> CoreResult<()> {
    if values.into_iter().any(|value| value.trim().is_empty()) {
        return Err(CoreError::InvalidPlan(
            "required planning text must be non-empty".into(),
        ));
    }
    Ok(())
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum PlanStatus {
    Proposal,
    Active,
    Superseded,
    Stale,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct PlanProposal {
    pub schema: String,
    pub id: Uuid,
    pub mode: PlanMode,
    pub target: PlanTarget,
    pub proposal_version: u64,
    pub expected_active_version: u64,
    pub body: PlanBody,
    pub assumptions: Vec<String>,
    pub open_questions: Vec<String>,
    pub dependency_fingerprints: BTreeMap<String, String>,
    pub fingerprint: String,
    pub status: PlanStatus,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct PlanProposalInput {
    pub mode: PlanMode,
    pub node_id: String,
    pub expected_active_version: u64,
    pub body: PlanBody,
    pub assumptions: Vec<String>,
    pub open_questions: Vec<String>,
    pub dependency_fingerprints: BTreeMap<String, String>,
}

impl PlanProposal {
    pub fn create(graph: &StoryGraph, input: PlanProposalInput) -> CoreResult<Self> {
        let PlanProposalInput {
            mode,
            node_id,
            expected_active_version,
            body,
            assumptions,
            open_questions,
            dependency_fingerprints,
        } = input;
        let target = PlanTarget::resolve(graph, mode, &node_id)?;
        if body.kind() != target.kind {
            return Err(CoreError::InvalidPlan(
                "plan body does not match target kind".into(),
            ));
        }
        body.validate()?;
        for (reference, fingerprint) in &dependency_fingerprints {
            if !reference.contains(':') || !is_fingerprint(fingerprint) {
                return Err(CoreError::InvalidPlan(
                    "dependency binding is not canonical".into(),
                ));
            }
        }
        let mut value = Self {
            schema: "quillframe_typed_plan_proposal_v1".into(),
            id: Uuid::new_v4(),
            mode,
            target,
            proposal_version: 1,
            expected_active_version,
            body,
            assumptions,
            open_questions,
            dependency_fingerprints,
            fingerprint: String::new(),
            status: PlanStatus::Proposal,
        };
        value.fingerprint = value.compute_fingerprint()?;
        Ok(value)
    }

    fn compute_fingerprint(&self) -> CoreResult<String> {
        let mut projection = self.clone();
        projection.fingerprint.clear();
        // Lifecycle is mutable ledger state, not part of the immutable proposal artifact.
        projection.status = PlanStatus::Proposal;
        let bytes = serde_json::to_vec(&projection)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        Ok(sha256_fingerprint(bytes))
    }

    pub fn validate_fingerprint(&self) -> CoreResult<()> {
        if self.fingerprint != self.compute_fingerprint()? {
            return Err(CoreError::InvalidPlan(
                "proposal fingerprint does not match exact content".into(),
            ));
        }
        Ok(())
    }
}

fn is_fingerprint(value: &str) -> bool {
    value.len() == 71
        && value.starts_with("sha256:")
        && value[7..]
            .chars()
            .all(|character| character.is_ascii_hexdigit())
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ActivePlan {
    pub proposal: PlanProposal,
    pub active_version: u64,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct AuthorActivation {
    pub schema: String,
    pub decision_id: Uuid,
    pub proposal_id: Uuid,
    pub proposal_fingerprint: String,
    pub expected_active_version: u64,
    pub authorized_by: String,
    pub decided_at: String,
    pub idempotency_key: String,
    pub fingerprint: String,
}

impl AuthorActivation {
    pub fn authorize(
        proposal: &PlanProposal,
        authorized_by: impl Into<String>,
        decided_at: impl Into<String>,
        idempotency_key: impl Into<String>,
    ) -> CoreResult<Self> {
        proposal.validate_fingerprint()?;
        let mut value = Self {
            schema: "quillframe_author_plan_activation_v1".into(),
            decision_id: Uuid::new_v4(),
            proposal_id: proposal.id,
            proposal_fingerprint: proposal.fingerprint.clone(),
            expected_active_version: proposal.expected_active_version,
            authorized_by: authorized_by.into(),
            decided_at: decided_at.into(),
            idempotency_key: idempotency_key.into(),
            fingerprint: String::new(),
        };
        value.validate_fields()?;
        value.fingerprint = value.compute_fingerprint()?;
        Ok(value)
    }

    pub fn validate(&self) -> CoreResult<()> {
        self.validate_fields()?;
        if self.fingerprint != self.compute_fingerprint()? {
            return Err(CoreError::AuthorityConflict(
                "author activation receipt fingerprint changed".into(),
            ));
        }
        Ok(())
    }

    fn validate_fields(&self) -> CoreResult<()> {
        if self.schema != "quillframe_author_plan_activation_v1"
            || self.authorized_by.trim().is_empty()
            || self.decided_at.trim().is_empty()
            || self.idempotency_key.trim().is_empty()
            || !is_fingerprint(&self.proposal_fingerprint)
        {
            return Err(CoreError::AuthorityConflict(
                "author activation receipt is incomplete".into(),
            ));
        }
        Ok(())
    }

    fn compute_fingerprint(&self) -> CoreResult<String> {
        let mut copy = self.clone();
        copy.fingerprint.clear();
        let bytes = serde_json::to_vec(&copy)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        Ok(sha256_fingerprint(bytes))
    }
}

#[derive(Clone, Debug, Default)]
pub struct PlanLedger {
    proposals: HashMap<Uuid, PlanProposal>,
    active: HashMap<String, ActivePlan>,
    idempotency: HashMap<String, (Uuid, u64)>,
}

impl PlanLedger {
    pub fn save_proposal(&mut self, proposal: PlanProposal) -> CoreResult<()> {
        proposal.validate_fingerprint()?;
        if proposal.status != PlanStatus::Proposal {
            return Err(CoreError::InvalidPlan(
                "only proposal status may enter proposal storage".into(),
            ));
        }
        if self.proposals.insert(proposal.id, proposal).is_some() {
            return Err(CoreError::AuthorityConflict(
                "proposal id already exists".into(),
            ));
        }
        Ok(())
    }

    pub fn activate(&mut self, authorization: &AuthorActivation) -> CoreResult<&ActivePlan> {
        authorization.validate()?;
        if let Some((prior_id, prior_version)) =
            self.idempotency.get(&authorization.idempotency_key)
        {
            if *prior_id != authorization.proposal_id {
                return Err(CoreError::AuthorityConflict(
                    "idempotency key was used for a different proposal".into(),
                ));
            }
            let proposal = self.proposals.get(prior_id).unwrap();
            return self
                .active
                .get(&proposal.target.reference)
                .filter(|active| active.active_version == *prior_version)
                .ok_or_else(|| {
                    CoreError::AuthorityConflict(
                        "idempotent activation is no longer current".into(),
                    )
                });
        }
        let proposal = self
            .proposals
            .get(&authorization.proposal_id)
            .cloned()
            .ok_or_else(|| CoreError::AuthorityConflict("proposal does not exist".into()))?;
        proposal.validate_fingerprint()?;
        if proposal.fingerprint != authorization.proposal_fingerprint {
            return Err(CoreError::AuthorityConflict(
                "proposal fingerprint changed".into(),
            ));
        }
        let current_version = self
            .active
            .get(&proposal.target.reference)
            .map_or(0, |active| active.active_version);
        if current_version != authorization.expected_active_version
            || proposal.expected_active_version != authorization.expected_active_version
        {
            return Err(CoreError::AuthorityConflict(
                "active plan version changed".into(),
            ));
        }
        if let Some(current) = self.active.get_mut(&proposal.target.reference) {
            current.proposal.status = PlanStatus::Superseded;
        }
        let proposal_id = proposal.id;
        let target_reference = proposal.target.reference.clone();
        let mut activated = proposal;
        activated.status = PlanStatus::Active;
        let version = current_version + 1;
        self.proposals.insert(activated.id, activated.clone());
        self.active.insert(
            activated.target.reference.clone(),
            ActivePlan {
                proposal: activated,
                active_version: version,
            },
        );
        self.idempotency.insert(
            authorization.idempotency_key.clone(),
            (proposal_id, version),
        );
        Ok(self.active.get(&target_reference).unwrap())
    }

    pub fn active(&self, target_ref: &str) -> Option<&ActivePlan> {
        self.active.get(target_ref)
    }
}

#[cfg(test)]
pub(crate) fn fixture_hierarchical_plan_lock() -> HierarchicalPlanLock {
    let graph = StoryGraph::bootstrap("测试长篇").unwrap();
    let mut layers = Vec::new();
    let book = PlanProposal::create(
        &graph,
        PlanProposalInput {
            mode: PlanMode::DesignBook,
            node_id: "BOOK".into(),
            expected_active_version: 0,
            body: PlanBody::Book(BookPlan {
                reader_promise: "主角以主动选择改变困局".into(),
                protagonist_agency: "每次升级来自行动与代价".into(),
                central_conflict: "追查真相与守护同伴冲突".into(),
                progression: vec!["从逃亡者成长为破局者".into()],
                endgame_reserve: vec!["幕后契约真相".into()],
                anti_exhaustion_limits: vec!["不提前透支终局真相".into()],
            }),
            assumptions: vec![],
            open_questions: vec![],
            dependency_fingerprints: BTreeMap::new(),
        },
    )
    .unwrap();
    layers.push(FrozenPlanLayer::from_active(&book, 1).unwrap());

    let book_dependency = BTreeMap::from([("book:BOOK".into(), book.fingerprint.clone())]);
    let volume = PlanProposal::create(
        &graph,
        PlanProposalInput {
            mode: PlanMode::DesignVolume,
            node_id: "VOL001".into(),
            expected_active_version: 0,
            body: PlanBody::Volume(VolumePlan {
                volume_promise: "主角摆脱第一轮追捕并发现更大敌人".into(),
                net_situation_change: "从被动逃亡转为主动追查".into(),
                opposition: "追兵与内部背叛".into(),
                relationship_movements: vec!["与同伴建立互信".into()],
                climax: "在封锁中反向设局".into(),
                inherited_debts: vec!["死者身份".into()],
            }),
            assumptions: vec![],
            open_questions: vec![],
            dependency_fingerprints: book_dependency.clone(),
        },
    )
    .unwrap();
    layers.push(FrozenPlanLayer::from_active(&volume, 1).unwrap());

    let unit_dependencies = BTreeMap::from([
        ("book:BOOK".into(), book.fingerprint.clone()),
        ("volume:VOL001".into(), volume.fingerprint.clone()),
    ]);
    let unit = PlanProposal::create(
        &graph,
        PlanProposalInput {
            mode: PlanMode::PlanUnit,
            node_id: "UNIT001".into(),
            expected_active_version: 0,
            body: PlanBody::Unit(UnitPlan {
                loop_question: "主角能否带同伴穿过封锁？".into(),
                setup: vec!["追兵封路".into()],
                release: "找到维修井".into(),
                aftermath: "身份暴露".into(),
                rewards: vec!["同伴获救".into()],
                delay_costs: vec!["追兵锁定主角".into()],
                foreshadowing: vec!["死者现身".into()],
                callbacks: vec![],
            }),
            assumptions: vec![],
            open_questions: vec![],
            dependency_fingerprints: unit_dependencies.clone(),
        },
    )
    .unwrap();
    layers.push(FrozenPlanLayer::from_active(&unit, 1).unwrap());

    let chapter_dependencies = BTreeMap::from([
        ("book:BOOK".into(), book.fingerprint.clone()),
        ("volume:VOL001".into(), volume.fingerprint.clone()),
        ("unit:UNIT001".into(), unit.fingerprint.clone()),
    ]);
    let chapter = PlanProposal::create(
        &graph,
        PlanProposalInput {
            mode: PlanMode::PlanChapter,
            node_id: "CH001".into(),
            expected_active_version: 0,
            body: chapter_body_fixture(),
            assumptions: vec![],
            open_questions: vec![],
            dependency_fingerprints: chapter_dependencies,
        },
    )
    .unwrap();
    layers.push(FrozenPlanLayer::from_active(&chapter, 1).unwrap());
    HierarchicalPlanLock::freeze(layers).unwrap()
}

#[cfg(test)]
fn chapter_body_fixture() -> PlanBody {
    PlanBody::Chapter(ChapterPlan {
        reader_contract: ReaderContract {
            reader_question: "他能否脱身？".into(),
            visible_reward: "发现出口".into(),
            character_choice: "返回救人".into(),
            cost: "暴露身份".into(),
            net_change: "同伴获救，追兵锁定他".into(),
            next_pull: "追兵先一步封住出口".into(),
        },
        constraint_lock: ChapterConstraintLock {
            length: LengthBand {
                min: 2800,
                max: 3800,
                unit: LengthUnit::ChineseCharacters,
            },
            must_happen: vec![ConstraintClause {
                id: "rescue".into(),
                statement: "主角必须返身救出同伴".into(),
            }],
            must_not_happen: vec![],
            exact_time_anchors: vec![],
            stop_point: "追兵先一步封住出口时停笔".into(),
            end_debt: "追兵先一步封住出口".into(),
        },
        scenes: vec![SceneObjective {
            scene_id: "SC001".into(),
            ordinal: 1,
            viewpoint: "主角".into(),
            location: "废弃车站".into(),
            entry_state: "被追兵分隔".into(),
            objective: "找到同伴".into(),
            opposition: "出口被封".into(),
            turn: "主角发现维修井".into(),
            exit_state: "救出同伴但身份暴露".into(),
            emotion_target: "先压迫，再因主动返身救人释放热血".into(),
            reader_effect: "担心代价，同时认可主角选择".into(),
        }],
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn chapter_body() -> PlanBody {
        chapter_body_fixture()
    }

    #[test]
    fn proposal_requires_exact_author_activation() {
        let graph = StoryGraph::bootstrap("第一章").unwrap();
        let proposal = PlanProposal::create(
            &graph,
            PlanProposalInput {
                mode: PlanMode::PlanChapter,
                node_id: "CH001".into(),
                expected_active_version: 0,
                body: chapter_body(),
                assumptions: vec![],
                open_questions: vec![],
                dependency_fingerprints: BTreeMap::new(),
            },
        )
        .unwrap();
        let fingerprint = proposal.fingerprint.clone();
        let id = proposal.id;
        let mut ledger = PlanLedger::default();
        ledger.save_proposal(proposal).unwrap();
        let authorization = AuthorActivation::authorize(
            ledger.proposals.get(&id).unwrap(),
            "author:local",
            "2026-08-31T00:00:00Z",
            "activate-1",
        )
        .unwrap();
        assert_eq!(authorization.proposal_fingerprint, fingerprint);
        let active = ledger.activate(&authorization).unwrap();
        assert_eq!(active.active_version, 1);
        assert_eq!(active.proposal.status, PlanStatus::Active);
        active.proposal.validate_fingerprint().unwrap();
    }

    #[test]
    fn target_and_body_kind_cannot_be_spoofed() {
        let graph = StoryGraph::bootstrap("第一章").unwrap();
        let result = PlanProposal::create(
            &graph,
            PlanProposalInput {
                mode: PlanMode::PlanChapter,
                node_id: "CH001".into(),
                expected_active_version: 0,
                body: PlanBody::Unit(UnitPlan {
                    loop_question: "问题".into(),
                    setup: vec![],
                    release: "释放".into(),
                    aftermath: "余波".into(),
                    rewards: vec![],
                    delay_costs: vec![],
                    foreshadowing: vec![],
                    callbacks: vec![],
                }),
                assumptions: vec![],
                open_questions: vec![],
                dependency_fingerprints: BTreeMap::new(),
            },
        );
        assert!(result.is_err());
    }

    #[test]
    fn chapter_constraint_lock_rejects_drift_and_plan_lock_requires_four_layers() {
        let graph = StoryGraph::bootstrap("第一章").unwrap();
        let mut body = chapter_body();
        if let PlanBody::Chapter(chapter) = &mut body {
            chapter.constraint_lock.end_debt = "另一个章尾承诺".into();
        }
        assert!(PlanProposal::create(
            &graph,
            PlanProposalInput {
                mode: PlanMode::PlanChapter,
                node_id: "CH001".into(),
                expected_active_version: 0,
                body,
                assumptions: vec![],
                open_questions: vec![],
                dependency_fingerprints: BTreeMap::new(),
            },
        )
        .is_err());

        let mut lock = fixture_hierarchical_plan_lock();
        lock.layers.remove(1);
        assert!(lock.validate().is_err());
    }
}
