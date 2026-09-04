//! Authoritative Quillframe fiction-production core.
//!
//! Studio is a presentation surface.  This crate owns typed project identity,
//! story hierarchy, planning authority, sparse context, and the durable
//! boundaries that later storage/runtime crates execute.

pub mod bridge;
pub mod context;
pub mod corpus;
pub mod corpus_store;
pub mod decisions;
pub mod error;
pub mod events;
pub mod execution;
mod fingerprint;
pub mod global_schema;
pub mod global_store;
pub mod guidance;
pub mod learning;
pub mod model;
pub mod planning;
pub mod production;
pub mod project;
pub mod prompt;
pub mod publication;
pub mod review;
pub mod schema;
pub mod semantic;
pub mod setup;
pub mod store;
pub mod story;
pub mod tracking;

pub use bridge::{BridgeRequest, HostBridgeRuntime};
pub use context::{
    ContextEntry, ContextFreeze, ContextManifest, ContextQueryPlan, ContextSelectionProposal,
    ContextStage, ContextTier,
};
pub use corpus::{
    AnalyzeStage, ChapterBoundary, CorpusArtifact, CorpusMechanism, CorpusProgress, CorpusQuality,
    EvidenceAnchor, SourceFreeCorpusPack, WriterCorpusMechanism, WriterCorpusProjection,
    WriterCorpusSelection,
};
pub use corpus_store::{
    CorpusDatabase, CorpusSelectionProjection, CorpusStageDispatch, CorpusStudyProjection,
    CorpusWorkProjection,
};
pub use decisions::{
    AcceptanceDecision, RevisionRequest, SettlementAuthorization, SettlementPreflight,
};
pub use error::{CoreError, CoreResult};
pub use events::{StoryEvent, StoryStateSnapshot};
pub use execution::{
    BoundRuleMaterial, ProductionIntent, ProductionRequest, ProductionTaskMode, RepairBinding,
    StageCall, StageCallState, StageJob,
};
pub use global_schema::{apply_fresh_global_schema, validate_current_global_schema};
pub use global_store::{GlobalDatabase, ModelServiceRecord, RegisteredProject};
pub use guidance::{
    expected_rule_ids, framework_guidance_fingerprint, FrozenGuidanceSource,
    ProductionGuidanceSnapshot, ProjectGuidanceInput,
};
pub use learning::{
    FeedbackCaptureDecision, FeedbackInterpretation, PreferenceReviewDecision,
    PreferenceReviewResult, WriterPreferenceProjection, WriterPreferenceSelection,
};
pub use model::{
    AuthStyle, ModelCatalog, ModelDescriptor, ModelRequest, ModelResult, ModelRuntime, ModelUsage,
    ProtocolFamily, SecretStore, ServiceEndpoint,
};
pub use planning::{
    ActivePlan, AuthorActivation, BookPlan, ChapterConstraintLock, ChapterContract, ChapterPlan,
    CharacterArcPlan, ConstraintClause, FrozenPlanLayer, HierarchicalPlanLock, LengthBand,
    LengthUnit, PlanBody, PlanLedger, PlanMode, PlanProposal, PlanProposalInput, PlanStatus,
    PlanTarget, ReaderContract, RelationshipArcPlan, SceneObjective, SceneScript, StoryFoundation,
    UnitPlan, VolumePlan,
};
pub use production::{
    CandidateArtifact, ProductionPipeline, ProductionRelease, ProductionState, SceneWritingBrief,
    WriterContinuityEntry, WriterPack,
};
pub use project::{ProjectContext, ProjectManifest};
pub use prompt::{PromptAssembly, PromptBlock};
pub use publication::{
    PublicationArtifact, PublicationBuild, PublicationFormat, PublicationPreview,
};
pub use review::{
    FindingCategory, ReviewDecision, ReviewFinding, ReviewMode, ReviewReport, ReviewReportInput,
    Severity,
};
pub use schema::{apply_fresh_project_schema, validate_current_project_schema};
pub use semantic::{
    ChapterTrackingProposal, CharacterAction, CharacterKnowledgeDelta, CharacterSimulation,
    DirectorNote, ExpectationDeltaAction, NarrativeEntityDelta, NarrativeEntityKind,
    ReaderExpectationDelta, RelationshipStateDelta, RepairComparison, RepairComparisonOutcome,
    RepairGenerationMode, RepairSpec, RepairTarget, ResolvedScene, SceneResolution,
    SemanticFinding, SemanticGate, SemanticGateDecision, SurfaceAuditDecision,
    SurfaceHardRuleAudit, SurfaceRealization, SurfaceRuleAssessment, SurfaceRuleStatus,
    TimelineEventDelta,
};
pub use setup::{
    ArcMilestoneSeed, BookSetupApprovalReceipt, BookSetupArtifact, BookSetupProposalReceipt,
    BookSetupSimulationProjection, BookSetupSourceEvidence, BookStructureSeed, CastEvolutionPolicy,
    CharacterBible, CharacterCharmArcSeed, CharacterCharmBeatSeed, CharacterVoiceProfile,
    ClimaxSeed, FixedEndingSeed, LongFormArchitecture, MacroCanonPolicy, MacroPartSeed,
    NarrativeArcKind, NarrativeArcSeed, ProgressionLadderSeed, RelationshipBible,
    RollingOutlinePolicy, SelectiveContextPolicy, VolumeBlueprintSeed, VolumeTurnSeed, WorldSeed,
    BOOK_SETUP_SCHEMA,
};
pub use store::{NativeProject, ProjectDatabase};
pub use story::{StoryGraph, StoryKind, StoryNode};
pub use tracking::{ChapterTrackingRecord, DerivedTrackingContext, TrackingLedger, TrackingState};
