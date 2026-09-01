use thiserror::Error;

pub type CoreResult<T> = Result<T, CoreError>;

#[derive(Debug, Error, Eq, PartialEq)]
pub enum CoreError {
    #[error("invalid project contract: {0}")]
    InvalidProject(String),
    #[error("invalid story hierarchy: {0}")]
    InvalidHierarchy(String),
    #[error("invalid plan contract: {0}")]
    InvalidPlan(String),
    #[error("authority conflict: {0}")]
    AuthorityConflict(String),
    #[error("context boundary violation: {0}")]
    ContextBoundary(String),
    #[error("serialization failed: {0}")]
    Serialization(String),
    #[error("storage contract failed: {0}")]
    Storage(String),
    #[error("model runtime failed: {0}")]
    ModelRuntime(String),
}
