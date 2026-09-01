//! Native, handle-bound filesystem primitives for Quillframe.
//!
//! The API is deliberately narrow: Rust Core owns fiction-domain persistence
//! and orchestration, while this crate owns path traversal, object identity,
//! sharing/rename exclusion, and platform fail-closed behavior.

use std::cell::RefCell;
use std::ffi::{c_void, OsStr};
#[cfg(any(windows, target_os = "linux"))]
use std::fs::File;
use std::path::{Component, Path, PathBuf};
use std::ptr;
use std::slice;
use std::sync::atomic::{AtomicU64, Ordering};

const STATUS_OK: i32 = 0;
const STATUS_INVALID_ARGUMENT: i32 = 1;
#[cfg(not(any(windows, target_os = "linux")))]
const STATUS_UNSUPPORTED: i32 = 2;
const STATUS_PATH_REJECTED: i32 = 3;
const STATUS_CONFLICT: i32 = 4;
const STATUS_IO: i32 = 5;
const STATUS_IDENTITY: i32 = 6;
static STAGE_SEQUENCE: AtomicU64 = AtomicU64::new(1);

thread_local! {
    static LAST_ERROR: RefCell<String> = const { RefCell::new(String::new()) };
}

fn fail(code: i32, message: impl Into<String>) -> i32 {
    LAST_ERROR.with(|slot| *slot.borrow_mut() = message.into());
    code
}

#[repr(C)]
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct QfNativeIdentity {
    pub volume_id: u64,
    pub file_id_low: u64,
    pub file_id_high: u64,
    pub link_count: u64,
    pub byte_size: u64,
    pub attributes: u32,
    pub reparse_tag: u32,
}

#[cfg(windows)]
type RawHandle = *mut c_void;

#[cfg(windows)]
struct GuardHandles(Vec<RawHandle>);

#[cfg(target_os = "linux")]
struct GuardHandles(Vec<File>);

#[cfg(not(any(windows, target_os = "linux")))]
struct GuardHandles;

#[repr(C)]
pub struct QfNativeGuard {
    path: PathBuf,
    identity: QfNativeIdentity,
    is_directory: bool,
    require_single_link: bool,
    share_delete: bool,
    handles: GuardHandles,
}

pub struct QfNativeLock {
    guard: QfNativeGuard,
}

#[derive(Debug, thiserror::Error)]
#[error("native filesystem error {code}: {message}")]
pub struct NativeError {
    pub code: i32,
    pub message: String,
}

impl QfNativeGuard {
    pub fn path(&self) -> &Path {
        &self.path
    }

    pub fn identity(&self) -> QfNativeIdentity {
        self.identity
    }

    pub fn revalidate(&self) -> Result<QfNativeIdentity, NativeError> {
        platform::revalidate(self).map_err(|code| NativeError {
            code,
            message: last_error_message(),
        })
    }
}

impl QfNativeLock {
    pub fn try_acquire(path: &Path) -> Result<Self, NativeError> {
        let guard = guard_file(path, FileMode::OpenOrCreate, true)?;
        platform::try_lock(&guard).map_err(|code| NativeError {
            code,
            message: last_error_message(),
        })?;
        if let Err(error) = guard.revalidate() {
            platform::unlock(&guard);
            return Err(error);
        }
        Ok(Self { guard })
    }

    pub fn path(&self) -> &Path {
        self.guard.path()
    }

    pub fn identity(&self) -> QfNativeIdentity {
        self.guard.identity()
    }
}

impl Drop for QfNativeLock {
    fn drop(&mut self) {
        platform::unlock(&self.guard);
    }
}

fn last_error_message() -> String {
    LAST_ERROR.with(|slot| slot.borrow().clone())
}

fn native_result(value: Result<QfNativeGuard, i32>) -> Result<QfNativeGuard, NativeError> {
    value.map_err(|code| NativeError {
        code,
        message: last_error_message(),
    })
}

fn same_object(left: QfNativeIdentity, right: QfNativeIdentity) -> bool {
    left.volume_id == right.volume_id
        && left.file_id_low == right.file_id_low
        && left.file_id_high == right.file_id_high
}

pub fn guard_directory(path: &Path, create: bool) -> Result<QfNativeGuard, NativeError> {
    validate_lexical_path(path).map_err(|code| NativeError {
        code,
        message: last_error_message(),
    })?;
    native_result(platform::directory(path, create))
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum FileMode {
    OpenRead,
    OpenReadWrite,
    CreateNew,
    OpenOrCreate,
    CreatePublishStage,
    OpenPublishStage,
}

pub fn guard_file(
    path: &Path,
    mode: FileMode,
    require_single_link: bool,
) -> Result<QfNativeGuard, NativeError> {
    validate_lexical_path(path).map_err(|code| NativeError {
        code,
        message: last_error_message(),
    })?;
    let mode = match mode {
        FileMode::OpenRead => 0,
        FileMode::OpenReadWrite => 1,
        FileMode::CreateNew => 2,
        FileMode::OpenOrCreate => 3,
        FileMode::CreatePublishStage => 4,
        FileMode::OpenPublishStage => 5,
    };
    native_result(platform::file(path, mode, require_single_link))
}

/// Writes a new file through a same-directory stage, flushes its content, and
/// publishes it without replacing an existing target.
pub fn atomic_write_new(path: &Path, bytes: &[u8]) -> Result<QfNativeGuard, NativeError> {
    validate_lexical_path(path).map_err(|code| NativeError {
        code,
        message: last_error_message(),
    })?;
    let parent = path.parent().ok_or_else(|| NativeError {
        code: STATUS_PATH_REJECTED,
        message: "atomic target has no parent".into(),
    })?;
    let target_name = path.file_name().ok_or_else(|| NativeError {
        code: STATUS_PATH_REJECTED,
        message: "atomic target has no file name".into(),
    })?;
    let parent_guard = guard_directory(parent, false)?;
    let sequence = STAGE_SEQUENCE.fetch_add(1, Ordering::Relaxed);
    let stage_name = format!(".qf-stage-{}-{sequence}", std::process::id());
    let stage_path = parent.join(&stage_name);
    let stage_guard = guard_file(&stage_path, FileMode::CreatePublishStage, true)?;
    platform::write_all(&stage_guard, bytes).map_err(|code| NativeError {
        code,
        message: last_error_message(),
    })?;
    platform::sync_file(&stage_guard).map_err(|code| NativeError {
        code,
        message: last_error_message(),
    })?;
    let staged_identity = stage_guard.revalidate()?;
    platform::publish_noreplace(
        &parent_guard,
        &stage_guard,
        OsStr::new(&stage_name),
        target_name,
    )
    .map_err(|code| NativeError {
        code,
        message: last_error_message(),
    })?;
    drop(stage_guard);
    parent_guard.revalidate()?;
    let published = guard_file(path, FileMode::OpenReadWrite, true).map_err(|mut error| {
        error.message = format!("published reopen: {}", error.message);
        error
    })?;
    let published_identity = published.revalidate().map_err(|mut error| {
        error.message = format!("published revalidation: {}", error.message);
        error
    })?;
    if !same_object(staged_identity, published_identity)
        || published_identity.byte_size != bytes.len() as u64
    {
        return Err(NativeError {
            code: STATUS_IDENTITY,
            message: "published file does not match the flushed stage".into(),
        });
    }
    Ok(published)
}

/// Creates and durably flushes an explicitly named stage file. The caller may
/// persist the returned identity before publishing it in a later recovery step.
pub fn write_stage_new(path: &Path, bytes: &[u8]) -> Result<QfNativeGuard, NativeError> {
    validate_lexical_path(path).map_err(|code| NativeError {
        code,
        message: last_error_message(),
    })?;
    let guard = guard_file(path, FileMode::CreatePublishStage, true)?;
    platform::write_all(&guard, bytes).map_err(|code| NativeError {
        code,
        message: last_error_message(),
    })?;
    platform::sync_file(&guard).map_err(|code| NativeError {
        code,
        message: last_error_message(),
    })?;
    let identity = guard.revalidate()?;
    if identity.byte_size != bytes.len() as u64 {
        return Err(NativeError {
            code: STATUS_IDENTITY,
            message: "staged file size does not match the flushed bytes".into(),
        });
    }
    Ok(guard)
}

/// Publishes a previously flushed same-directory stage without replacing an
/// existing target, then proves the final path names the exact staged object.
pub fn publish_staged_noreplace(
    stage_path: &Path,
    final_path: &Path,
    expected_identity: QfNativeIdentity,
) -> Result<QfNativeGuard, NativeError> {
    validate_lexical_path(stage_path).map_err(|code| NativeError {
        code,
        message: last_error_message(),
    })?;
    validate_lexical_path(final_path).map_err(|code| NativeError {
        code,
        message: last_error_message(),
    })?;
    let parent = stage_path.parent().ok_or_else(|| NativeError {
        code: STATUS_PATH_REJECTED,
        message: "publication stage has no parent".into(),
    })?;
    if final_path.parent() != Some(parent) {
        return Err(NativeError {
            code: STATUS_PATH_REJECTED,
            message: "publication stage and target must share one directory".into(),
        });
    }
    let stage_name = stage_path.file_name().ok_or_else(|| NativeError {
        code: STATUS_PATH_REJECTED,
        message: "publication stage has no file name".into(),
    })?;
    let final_name = final_path.file_name().ok_or_else(|| NativeError {
        code: STATUS_PATH_REJECTED,
        message: "publication target has no file name".into(),
    })?;
    let parent_guard = guard_directory(parent, false)?;
    let stage_guard = guard_file(stage_path, FileMode::OpenPublishStage, true)?;
    let staged_identity = stage_guard.revalidate()?;
    if !same_object(staged_identity, expected_identity)
        || staged_identity.byte_size != expected_identity.byte_size
    {
        return Err(NativeError {
            code: STATUS_IDENTITY,
            message: "publication stage identity changed before publish".into(),
        });
    }
    platform::publish_noreplace(&parent_guard, &stage_guard, stage_name, final_name).map_err(
        |code| NativeError {
            code,
            message: last_error_message(),
        },
    )?;
    drop(stage_guard);
    parent_guard.revalidate()?;
    let published = guard_file(final_path, FileMode::OpenRead, true)?;
    let published_identity = published.revalidate()?;
    if !same_object(published_identity, expected_identity)
        || published_identity.byte_size != expected_identity.byte_size
    {
        return Err(NativeError {
            code: STATUS_IDENTITY,
            message: "published target does not name the staged object".into(),
        });
    }
    Ok(published)
}

/// Reads through the guarded native handle and bounds memory before allocation.
pub fn read_guarded_file(
    path: &Path,
    maximum_bytes: u64,
) -> Result<(Vec<u8>, QfNativeIdentity), NativeError> {
    let guard = guard_file(path, FileMode::OpenRead, true)?;
    let before = guard.revalidate()?;
    if before.byte_size > maximum_bytes {
        return Err(NativeError {
            code: STATUS_INVALID_ARGUMENT,
            message: "guarded file exceeds the configured byte limit".into(),
        });
    }
    let bytes = platform::read_all(&guard, maximum_bytes).map_err(|code| NativeError {
        code,
        message: last_error_message(),
    })?;
    let after = guard.revalidate()?;
    if !same_object(before, after) || bytes.len() as u64 != after.byte_size {
        return Err(NativeError {
            code: STATUS_IDENTITY,
            message: "guarded file changed while it was read".into(),
        });
    }
    Ok((bytes, after))
}

fn parse_path(pointer: *const u8, length: usize) -> Result<PathBuf, i32> {
    if pointer.is_null() || length == 0 {
        return Err(fail(
            STATUS_INVALID_ARGUMENT,
            "path must be non-empty UTF-8",
        ));
    }
    let bytes = unsafe { slice::from_raw_parts(pointer, length) };
    let value = std::str::from_utf8(bytes)
        .map_err(|_| fail(STATUS_INVALID_ARGUMENT, "path must be valid UTF-8"))?;
    let path = PathBuf::from(value);
    validate_lexical_path(&path)?;
    Ok(path)
}

fn validate_lexical_path(path: &Path) -> Result<(), i32> {
    if !path.is_absolute() {
        return Err(fail(STATUS_PATH_REJECTED, "native path must be absolute"));
    }
    validate_platform_path(path)?;
    for component in path.components() {
        match component {
            Component::ParentDir | Component::CurDir => {
                return Err(fail(STATUS_PATH_REJECTED, "native path is not canonical"));
            }
            Component::Normal(value) => validate_component(value)?,
            Component::Prefix(_) | Component::RootDir => {}
        }
    }
    Ok(())
}

#[cfg(windows)]
fn validate_platform_path(path: &Path) -> Result<(), i32> {
    use std::path::Prefix;

    let mut components = path.components();
    let Some(Component::Prefix(prefix)) = components.next() else {
        return Err(fail(
            STATUS_PATH_REJECTED,
            "Windows paths require an explicit local drive",
        ));
    };
    if !matches!(prefix.kind(), Prefix::Disk(_))
        || !matches!(components.next(), Some(Component::RootDir))
    {
        return Err(fail(
            STATUS_PATH_REJECTED,
            "UNC, device, verbatim, and drive-relative paths are unsupported",
        ));
    }
    Ok(())
}

#[cfg(target_os = "linux")]
fn validate_platform_path(_: &Path) -> Result<(), i32> {
    Ok(())
}

#[cfg(not(any(windows, target_os = "linux")))]
fn validate_platform_path(_: &Path) -> Result<(), i32> {
    Err(fail(
        STATUS_UNSUPPORTED,
        "native filesystem backend is unavailable",
    ))
}

fn validate_component(component: &OsStr) -> Result<(), i32> {
    let value = component.to_string_lossy();
    if value.is_empty() || value.ends_with(' ') || value.ends_with('.') {
        return Err(fail(
            STATUS_PATH_REJECTED,
            "path component has an unsafe suffix",
        ));
    }
    if value
        .chars()
        .any(|character| character == ':' || character < '\u{20}')
    {
        return Err(fail(
            STATUS_PATH_REJECTED,
            "path component contains an alternate stream or control character",
        ));
    }
    #[cfg(windows)]
    {
        let stem = value
            .split('.')
            .next()
            .unwrap_or_default()
            .to_ascii_uppercase();
        let reserved = matches!(stem.as_str(), "CON" | "PRN" | "AUX" | "NUL")
            || stem
                .strip_prefix("COM")
                .or_else(|| stem.strip_prefix("LPT"))
                .is_some_and(|suffix| {
                    matches!(suffix, "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9")
                });
        if reserved {
            return Err(fail(
                STATUS_PATH_REJECTED,
                "path contains a reserved device name",
            ));
        }
    }
    Ok(())
}

#[cfg(windows)]
mod platform {
    use super::*;
    use std::os::windows::ffi::OsStrExt;

    const INVALID_HANDLE_VALUE: RawHandle = -1isize as RawHandle;
    const GENERIC_READ: u32 = 0x8000_0000;
    const GENERIC_WRITE: u32 = 0x4000_0000;
    const DELETE_ACCESS: u32 = 0x0001_0000;
    const FILE_READ_ATTRIBUTES: u32 = 0x0000_0080;
    const FILE_SHARE_READ: u32 = 0x0000_0001;
    const FILE_SHARE_WRITE: u32 = 0x0000_0002;
    const CREATE_NEW: u32 = 1;
    const OPEN_EXISTING: u32 = 3;
    const OPEN_ALWAYS: u32 = 4;
    const FILE_ATTRIBUTE_DIRECTORY: u32 = 0x0000_0010;
    const FILE_ATTRIBUTE_NORMAL: u32 = 0x0000_0080;
    const FILE_ATTRIBUTE_REPARSE_POINT: u32 = 0x0000_0400;
    const FILE_FLAG_WRITE_THROUGH: u32 = 0x8000_0000;
    const FILE_FLAG_OPEN_REPARSE_POINT: u32 = 0x0020_0000;
    const FILE_FLAG_BACKUP_SEMANTICS: u32 = 0x0200_0000;
    const ERROR_FILE_EXISTS: i32 = 80;
    const ERROR_ALREADY_EXISTS: i32 = 183;
    const FILE_ATTRIBUTE_TAG_INFO_CLASS: i32 = 9;
    const FILE_ID_INFO_CLASS: i32 = 18;
    const FILE_TYPE_DISK: u32 = 1;
    const FILE_RENAME_INFO_CLASS: i32 = 3;

    #[repr(C)]
    struct FileAttributeTagInfo {
        file_attributes: u32,
        reparse_tag: u32,
    }

    #[repr(C)]
    struct FileId128 {
        identifier: [u8; 16],
    }

    #[repr(C)]
    struct FileIdInfo {
        volume_serial_number: u64,
        file_id: FileId128,
    }

    #[repr(C)]
    struct FileRenameInfo {
        replace_if_exists: u32,
        root_directory: RawHandle,
        file_name_length: u32,
        file_name: [u16; 1],
    }

    #[repr(C)]
    struct FileTime {
        low: u32,
        high: u32,
    }

    #[repr(C)]
    struct ByHandleFileInformation {
        file_attributes: u32,
        creation_time: FileTime,
        last_access_time: FileTime,
        last_write_time: FileTime,
        volume_serial_number: u32,
        file_size_high: u32,
        file_size_low: u32,
        number_of_links: u32,
        file_index_high: u32,
        file_index_low: u32,
    }

    #[link(name = "kernel32")]
    extern "system" {
        fn CreateFileW(
            file_name: *const u16,
            desired_access: u32,
            share_mode: u32,
            security_attributes: *mut c_void,
            creation_disposition: u32,
            flags_and_attributes: u32,
            template_file: RawHandle,
        ) -> RawHandle;
        fn CreateDirectoryW(path_name: *const u16, security_attributes: *mut c_void) -> i32;
        fn CloseHandle(handle: RawHandle) -> i32;
        fn GetFileInformationByHandleEx(
            handle: RawHandle,
            info_class: i32,
            info: *mut c_void,
            size: u32,
        ) -> i32;
        fn GetFileInformationByHandle(handle: RawHandle, info: *mut ByHandleFileInformation)
            -> i32;
        fn GetFileType(handle: RawHandle) -> u32;
        fn GetLastError() -> u32;
        fn WriteFile(
            handle: RawHandle,
            buffer: *const c_void,
            bytes_to_write: u32,
            bytes_written: *mut u32,
            overlapped: *mut c_void,
        ) -> i32;
        fn ReadFile(
            handle: RawHandle,
            buffer: *mut c_void,
            bytes_to_read: u32,
            bytes_read: *mut u32,
            overlapped: *mut c_void,
        ) -> i32;
        fn FlushFileBuffers(handle: RawHandle) -> i32;
        fn SetFileInformationByHandle(
            file: RawHandle,
            information_class: i32,
            information: *mut c_void,
            buffer_size: u32,
        ) -> i32;
    }

    fn wide(path: &Path) -> Vec<u16> {
        let mut value = OsStr::new(r"\\?\").encode_wide().collect::<Vec<_>>();
        value.extend(path.as_os_str().encode_wide());
        value.push(0);
        value
    }

    fn io_error(message: &str) -> i32 {
        let error = unsafe { GetLastError() };
        fail(STATUS_IO, format!("{message} (win32={error})"))
    }

    fn identity(handle: RawHandle) -> Result<QfNativeIdentity, i32> {
        let mut tag = FileAttributeTagInfo {
            file_attributes: 0,
            reparse_tag: 0,
        };
        if unsafe {
            GetFileInformationByHandleEx(
                handle,
                FILE_ATTRIBUTE_TAG_INFO_CLASS,
                &mut tag as *mut _ as *mut c_void,
                std::mem::size_of::<FileAttributeTagInfo>() as u32,
            )
        } == 0
        {
            return Err(io_error("unable to query file attributes"));
        }
        let mut id = FileIdInfo {
            volume_serial_number: 0,
            file_id: FileId128 {
                identifier: [0; 16],
            },
        };
        if unsafe {
            GetFileInformationByHandleEx(
                handle,
                FILE_ID_INFO_CLASS,
                &mut id as *mut _ as *mut c_void,
                std::mem::size_of::<FileIdInfo>() as u32,
            )
        } == 0
        {
            return Err(io_error("unable to query stable file identity"));
        }
        let mut basic = unsafe { std::mem::zeroed::<ByHandleFileInformation>() };
        if unsafe { GetFileInformationByHandle(handle, &mut basic) } == 0 {
            return Err(io_error("unable to query file continuity"));
        }
        Ok(QfNativeIdentity {
            volume_id: id.volume_serial_number,
            file_id_low: u64::from_le_bytes(id.file_id.identifier[0..8].try_into().unwrap()),
            file_id_high: u64::from_le_bytes(id.file_id.identifier[8..16].try_into().unwrap()),
            link_count: basic.number_of_links as u64,
            byte_size: ((basic.file_size_high as u64) << 32) | basic.file_size_low as u64,
            attributes: tag.file_attributes,
            reparse_tag: tag.reparse_tag,
        })
    }

    fn open(
        path: &Path,
        directory: bool,
        disposition: u32,
        writable: bool,
        delete_access: bool,
        share_delete: bool,
    ) -> Result<(RawHandle, QfNativeIdentity), i32> {
        let access = GENERIC_READ
            | FILE_READ_ATTRIBUTES
            | if writable { GENERIC_WRITE } else { 0 }
            | if delete_access { DELETE_ACCESS } else { 0 };
        let flags = FILE_FLAG_OPEN_REPARSE_POINT
            | if directory {
                FILE_FLAG_BACKUP_SEMANTICS
            } else {
                FILE_ATTRIBUTE_NORMAL
            }
            | if writable { FILE_FLAG_WRITE_THROUGH } else { 0 };
        let handle = unsafe {
            CreateFileW(
                wide(path).as_ptr(),
                access,
                FILE_SHARE_READ | FILE_SHARE_WRITE | if share_delete { 0x0000_0004 } else { 0 },
                ptr::null_mut(),
                disposition,
                flags,
                ptr::null_mut(),
            )
        };
        if handle == INVALID_HANDLE_VALUE {
            let error = unsafe { GetLastError() } as i32;
            if error == ERROR_FILE_EXISTS || error == ERROR_ALREADY_EXISTS {
                return Err(fail(STATUS_CONFLICT, "native target already exists"));
            }
            return Err(io_error("unable to open protected path"));
        }
        if unsafe { GetFileType(handle) } != FILE_TYPE_DISK {
            unsafe { CloseHandle(handle) };
            return Err(fail(
                STATUS_PATH_REJECTED,
                "native path is not a local disk object",
            ));
        }
        match identity(handle) {
            Ok(token) => {
                if token.attributes & FILE_ATTRIBUTE_REPARSE_POINT != 0 {
                    unsafe { CloseHandle(handle) };
                    return Err(fail(STATUS_PATH_REJECTED, "reparse points are forbidden"));
                }
                let is_directory = token.attributes & FILE_ATTRIBUTE_DIRECTORY != 0;
                if is_directory != directory {
                    unsafe { CloseHandle(handle) };
                    return Err(fail(
                        STATUS_PATH_REJECTED,
                        "native path has the wrong object type",
                    ));
                }
                Ok((handle, token))
            }
            Err(code) => {
                unsafe { CloseHandle(handle) };
                Err(code)
            }
        }
    }

    fn chain_parts(path: &Path) -> Result<Vec<PathBuf>, i32> {
        let mut parts = Vec::new();
        let mut cursor = PathBuf::new();
        for component in path.components() {
            match component {
                Component::Prefix(prefix) => cursor.push(prefix.as_os_str()),
                Component::RootDir => {
                    cursor.push(Path::new(r"\"));
                    parts.push(cursor.clone());
                }
                Component::Normal(part) => {
                    cursor.push(part);
                    parts.push(cursor.clone());
                }
                Component::CurDir | Component::ParentDir => {
                    return Err(fail(STATUS_PATH_REJECTED, "native path is not canonical"));
                }
            }
        }
        if parts.is_empty() {
            return Err(fail(STATUS_PATH_REJECTED, "native path has no root"));
        }
        Ok(parts)
    }

    pub(super) fn directory(path: &Path, create: bool) -> Result<QfNativeGuard, i32> {
        let mut handles = Vec::new();
        let parts = chain_parts(path)?;
        for (index, part) in parts.iter().enumerate() {
            if create && index > 0 {
                let created = unsafe { CreateDirectoryW(wide(part).as_ptr(), ptr::null_mut()) };
                if created == 0 {
                    let error = unsafe { GetLastError() } as i32;
                    if error != ERROR_FILE_EXISTS && error != ERROR_ALREADY_EXISTS {
                        for handle in handles.drain(..).rev() {
                            unsafe { CloseHandle(handle) };
                        }
                        return Err(io_error("unable to create protected directory"));
                    }
                }
            }
            match open(part, true, OPEN_EXISTING, false, false, false) {
                Ok((handle, _)) => handles.push(handle),
                Err(code) => {
                    for handle in handles.drain(..).rev() {
                        unsafe { CloseHandle(handle) };
                    }
                    return Err(code);
                }
            }
        }
        let identity = identity(*handles.last().unwrap())?;
        Ok(QfNativeGuard {
            path: path.to_path_buf(),
            identity,
            is_directory: true,
            require_single_link: false,
            share_delete: false,
            handles: GuardHandles(handles),
        })
    }

    pub(super) fn file(
        path: &Path,
        mode: u32,
        require_single_link: bool,
    ) -> Result<QfNativeGuard, i32> {
        let parent = path
            .parent()
            .ok_or_else(|| fail(STATUS_PATH_REJECTED, "file path has no parent"))?;
        let mut parent_guard = directory(parent, false)?;
        let (disposition, writable, delete_access) = match mode {
            0 => (OPEN_EXISTING, false, false),
            1 => (OPEN_EXISTING, true, false),
            2 => (CREATE_NEW, true, false),
            3 => (OPEN_ALWAYS, true, false),
            4 => (CREATE_NEW, true, true),
            5 => (OPEN_EXISTING, true, true),
            _ => return Err(fail(STATUS_INVALID_ARGUMENT, "unknown native file mode")),
        };
        let (file_handle, identity) = open(
            path,
            false,
            disposition,
            writable,
            delete_access,
            delete_access,
        )?;
        if require_single_link && identity.link_count != 1 {
            unsafe { CloseHandle(file_handle) };
            return Err(fail(
                STATUS_IDENTITY,
                "native file must have exactly one hard link",
            ));
        }
        parent_guard.handles.0.push(file_handle);
        parent_guard.path = path.to_path_buf();
        parent_guard.identity = identity;
        parent_guard.is_directory = false;
        parent_guard.require_single_link = require_single_link;
        parent_guard.share_delete = delete_access;
        Ok(parent_guard)
    }

    pub(super) fn revalidate(guard: &QfNativeGuard) -> Result<QfNativeIdentity, i32> {
        let current = identity(*guard.handles.0.last().unwrap())?;
        if !same_object(current, guard.identity)
            || current.attributes & FILE_ATTRIBUTE_REPARSE_POINT != 0
            || (current.attributes & FILE_ATTRIBUTE_DIRECTORY != 0) != guard.is_directory
            || (guard.require_single_link && current.link_count != 1)
        {
            return Err(fail(
                STATUS_IDENTITY,
                "guarded object identity changed while open",
            ));
        }
        let (path_handle, path_identity) = open(
            &guard.path,
            guard.is_directory,
            OPEN_EXISTING,
            false,
            false,
            guard.share_delete,
        )?;
        unsafe { CloseHandle(path_handle) };
        if !same_object(current, path_identity)
            || (guard.require_single_link && path_identity.link_count != 1)
        {
            return Err(fail(
                STATUS_IDENTITY,
                "guarded path no longer names the opened object",
            ));
        }
        Ok(current)
    }

    pub(super) fn write_all(guard: &QfNativeGuard, bytes: &[u8]) -> Result<(), i32> {
        let handle = *guard.handles.0.last().unwrap();
        for chunk in bytes.chunks(u32::MAX as usize) {
            let mut written = 0_u32;
            if unsafe {
                WriteFile(
                    handle,
                    chunk.as_ptr() as *const c_void,
                    chunk.len() as u32,
                    &mut written,
                    ptr::null_mut(),
                )
            } == 0
            {
                return Err(io_error("native staged write failed"));
            }
            if written as usize != chunk.len() {
                return Err(fail(STATUS_IO, "native staged write was incomplete"));
            }
        }
        Ok(())
    }

    pub(super) fn read_all(guard: &QfNativeGuard, maximum_bytes: u64) -> Result<Vec<u8>, i32> {
        if guard.identity.byte_size > maximum_bytes || guard.identity.byte_size > usize::MAX as u64
        {
            return Err(fail(
                STATUS_INVALID_ARGUMENT,
                "guarded read exceeds the byte limit",
            ));
        }
        let mut bytes = vec![0_u8; guard.identity.byte_size as usize];
        let handle = *guard.handles.0.last().unwrap();
        let mut offset = 0_usize;
        while offset < bytes.len() {
            let chunk = (bytes.len() - offset).min(u32::MAX as usize);
            let mut read = 0_u32;
            if unsafe {
                ReadFile(
                    handle,
                    bytes[offset..].as_mut_ptr() as *mut c_void,
                    chunk as u32,
                    &mut read,
                    ptr::null_mut(),
                )
            } == 0
            {
                return Err(io_error("guarded native read failed"));
            }
            if read == 0 {
                return Err(fail(STATUS_IO, "guarded native read ended early"));
            }
            offset += read as usize;
        }
        Ok(bytes)
    }

    pub(super) fn sync_file(guard: &QfNativeGuard) -> Result<(), i32> {
        if unsafe { FlushFileBuffers(*guard.handles.0.last().unwrap()) } == 0 {
            return Err(io_error("native staged flush failed"));
        }
        Ok(())
    }

    pub(super) fn publish_noreplace(
        parent: &QfNativeGuard,
        stage: &QfNativeGuard,
        stage_name: &OsStr,
        target_name: &OsStr,
    ) -> Result<(), i32> {
        if stage.path.file_name() != Some(stage_name) {
            return Err(fail(
                STATUS_IDENTITY,
                "stage handle does not bind the requested name",
            ));
        }
        let mut name = wide(&parent.path.join(target_name));
        if name.last() == Some(&0) {
            name.pop();
        }
        if name.is_empty() {
            return Err(fail(
                STATUS_PATH_REJECTED,
                "publication target name is empty",
            ));
        }
        let header = std::mem::size_of::<FileRenameInfo>() - std::mem::size_of::<u16>();
        let mut buffer = vec![0_u8; header + name.len() * std::mem::size_of::<u16>()];
        let info = buffer.as_mut_ptr() as *mut FileRenameInfo;
        unsafe {
            (*info).replace_if_exists = 0;
            (*info).root_directory = ptr::null_mut();
            (*info).file_name_length = (name.len() * std::mem::size_of::<u16>()) as u32;
            std::ptr::copy_nonoverlapping(
                name.as_mut_ptr(),
                (*info).file_name.as_mut_ptr(),
                name.len(),
            );
        }
        if unsafe {
            SetFileInformationByHandle(
                *stage.handles.0.last().unwrap(),
                FILE_RENAME_INFO_CLASS,
                buffer.as_mut_ptr() as *mut c_void,
                buffer.len() as u32,
            )
        } == 0
        {
            let error = unsafe { GetLastError() } as i32;
            if error == ERROR_FILE_EXISTS || error == ERROR_ALREADY_EXISTS {
                return Err(fail(STATUS_CONFLICT, "atomic target already exists"));
            }
            return Err(io_error("handle-bound atomic publish failed"));
        }
        let _ = unsafe { FlushFileBuffers(*parent.handles.0.last().unwrap()) };
        Ok(())
    }

    pub(super) fn try_lock(guard: &QfNativeGuard) -> Result<(), i32> {
        use std::mem::ManuallyDrop;
        use std::os::windows::io::FromRawHandle;

        let file =
            ManuallyDrop::new(unsafe { File::from_raw_handle(*guard.handles.0.last().unwrap()) });
        fs2::FileExt::try_lock_exclusive(&*file)
            .map_err(|error| fail(STATUS_CONFLICT, format!("native lock is busy: {error}")))
    }

    pub(super) fn unlock(guard: &QfNativeGuard) {
        use std::mem::ManuallyDrop;
        use std::os::windows::io::FromRawHandle;

        let file =
            ManuallyDrop::new(unsafe { File::from_raw_handle(*guard.handles.0.last().unwrap()) });
        let _ = fs2::FileExt::unlock(&*file);
    }

    impl Drop for GuardHandles {
        fn drop(&mut self) {
            for handle in self.0.drain(..).rev() {
                unsafe { CloseHandle(handle) };
            }
        }
    }
}

#[cfg(target_os = "linux")]
mod platform {
    use super::*;
    use std::ffi::CString;
    use std::io::{Read, Write};
    use std::os::fd::{AsRawFd, FromRawFd, RawFd};
    use std::os::unix::ffi::OsStrExt;

    fn openat(directory: RawFd, name: &OsStr, flags: i32, mode: u32) -> Result<File, i32> {
        let name = CString::new(name.as_bytes())
            .map_err(|_| fail(STATUS_PATH_REJECTED, "path contains NUL"))?;
        let fd = unsafe { libc::openat(directory, name.as_ptr(), flags, mode) };
        if fd < 0 {
            let error = std::io::Error::last_os_error();
            if error.kind() == std::io::ErrorKind::AlreadyExists {
                return Err(fail(STATUS_CONFLICT, "native target already exists"));
            }
            return Err(fail(STATUS_IO, format!("native openat failed: {error}")));
        }
        Ok(unsafe { File::from_raw_fd(fd) })
    }

    fn identity(file: &File) -> Result<QfNativeIdentity, i32> {
        use std::os::unix::fs::MetadataExt;
        let value = file
            .metadata()
            .map_err(|error| fail(STATUS_IO, format!("native metadata failed: {error}")))?;
        Ok(QfNativeIdentity {
            volume_id: value.dev(),
            file_id_low: value.ino(),
            file_id_high: 0,
            link_count: value.nlink(),
            byte_size: value.size(),
            attributes: value.mode(),
            reparse_tag: 0,
        })
    }

    pub(super) fn directory(path: &Path, create: bool) -> Result<QfNativeGuard, i32> {
        use std::os::fd::AsRawFd;
        let root = File::open("/")
            .map_err(|error| fail(STATUS_IO, format!("unable to open root: {error}")))?;
        let mut handles = vec![root];
        for component in path.components() {
            let Component::Normal(name) = component else {
                continue;
            };
            let parent_fd = handles.last().unwrap().as_raw_fd();
            if create {
                let name_c = CString::new(name.as_bytes())
                    .map_err(|_| fail(STATUS_PATH_REJECTED, "path contains NUL"))?;
                let result = unsafe { libc::mkdirat(parent_fd, name_c.as_ptr(), 0o700) };
                if result != 0 {
                    let error = std::io::Error::last_os_error();
                    if error.kind() != std::io::ErrorKind::AlreadyExists {
                        return Err(fail(STATUS_IO, format!("native mkdirat failed: {error}")));
                    }
                }
            }
            handles.push(openat(
                parent_fd,
                name,
                libc::O_RDONLY | libc::O_DIRECTORY | libc::O_NOFOLLOW | libc::O_CLOEXEC,
                0,
            )?);
        }
        let token = identity(handles.last().unwrap())?;
        Ok(QfNativeGuard {
            path: path.to_path_buf(),
            identity: token,
            is_directory: true,
            require_single_link: false,
            share_delete: false,
            handles: GuardHandles(handles),
        })
    }

    pub(super) fn file(
        path: &Path,
        mode: u32,
        require_single_link: bool,
    ) -> Result<QfNativeGuard, i32> {
        use std::os::fd::AsRawFd;
        let parent = path
            .parent()
            .ok_or_else(|| fail(STATUS_PATH_REJECTED, "file path has no parent"))?;
        let mut guard = directory(parent, false)?;
        let name = path
            .file_name()
            .ok_or_else(|| fail(STATUS_PATH_REJECTED, "file path has no name"))?;
        let flags = match mode {
            0 => libc::O_RDONLY,
            1 | 5 => libc::O_RDWR,
            2 | 4 => libc::O_RDWR | libc::O_CREAT | libc::O_EXCL,
            3 => libc::O_RDWR | libc::O_CREAT,
            _ => return Err(fail(STATUS_INVALID_ARGUMENT, "unknown native file mode")),
        } | libc::O_NOFOLLOW
            | libc::O_CLOEXEC;
        let file = openat(
            guard.handles.0.last().unwrap().as_raw_fd(),
            name,
            flags,
            0o600,
        )?;
        let token = identity(&file)?;
        if token.attributes & libc::S_IFMT != libc::S_IFREG {
            return Err(fail(
                STATUS_PATH_REJECTED,
                "native file path is not a regular file",
            ));
        }
        if require_single_link && token.link_count != 1 {
            return Err(fail(
                STATUS_IDENTITY,
                "native file must have exactly one hard link",
            ));
        }
        guard.handles.0.push(file);
        guard.path = path.to_path_buf();
        guard.identity = token;
        guard.is_directory = false;
        guard.require_single_link = require_single_link;
        guard.share_delete = matches!(mode, 4 | 5);
        Ok(guard)
    }

    pub(super) fn revalidate(guard: &QfNativeGuard) -> Result<QfNativeIdentity, i32> {
        let current = identity(guard.handles.0.last().unwrap())?;
        if !same_object(current, guard.identity)
            || (guard.require_single_link && current.link_count != 1)
        {
            return Err(fail(
                STATUS_IDENTITY,
                "guarded object identity changed while open",
            ));
        }
        let reopened = if guard.is_directory {
            directory(&guard.path, false)?
        } else {
            file(&guard.path, 0, guard.require_single_link)?
        };
        let path_identity = reopened.identity;
        if !same_object(current, path_identity) {
            return Err(fail(
                STATUS_IDENTITY,
                "guarded path no longer names the opened object",
            ));
        }
        Ok(current)
    }

    pub(super) fn write_all(guard: &QfNativeGuard, bytes: &[u8]) -> Result<(), i32> {
        let mut file = guard.handles.0.last().unwrap();
        file.write_all(bytes)
            .map_err(|error| fail(STATUS_IO, format!("native staged write failed: {error}")))
    }

    pub(super) fn read_all(guard: &QfNativeGuard, maximum_bytes: u64) -> Result<Vec<u8>, i32> {
        if guard.identity.byte_size > maximum_bytes || guard.identity.byte_size > usize::MAX as u64
        {
            return Err(fail(
                STATUS_INVALID_ARGUMENT,
                "guarded read exceeds the byte limit",
            ));
        }
        let mut bytes = Vec::with_capacity(guard.identity.byte_size as usize);
        let mut file = guard.handles.0.last().unwrap();
        file.take(maximum_bytes.saturating_add(1))
            .read_to_end(&mut bytes)
            .map_err(|error| fail(STATUS_IO, format!("guarded native read failed: {error}")))?;
        if bytes.len() as u64 > maximum_bytes {
            return Err(fail(
                STATUS_INVALID_ARGUMENT,
                "guarded read exceeds the byte limit",
            ));
        }
        Ok(bytes)
    }

    pub(super) fn sync_file(guard: &QfNativeGuard) -> Result<(), i32> {
        guard
            .handles
            .0
            .last()
            .unwrap()
            .sync_all()
            .map_err(|error| fail(STATUS_IO, format!("native staged flush failed: {error}")))
    }

    pub(super) fn publish_noreplace(
        parent: &QfNativeGuard,
        _: &QfNativeGuard,
        stage_name: &OsStr,
        target_name: &OsStr,
    ) -> Result<(), i32> {
        let stage = CString::new(stage_name.as_bytes())
            .map_err(|_| fail(STATUS_PATH_REJECTED, "stage name contains NUL"))?;
        let target = CString::new(target_name.as_bytes())
            .map_err(|_| fail(STATUS_PATH_REJECTED, "target name contains NUL"))?;
        let parent_fd = parent.handles.0.last().unwrap().as_raw_fd();
        let result = unsafe {
            libc::syscall(
                libc::SYS_renameat2,
                parent_fd,
                stage.as_ptr(),
                parent_fd,
                target.as_ptr(),
                libc::RENAME_NOREPLACE,
            )
        };
        if result != 0 {
            let error = std::io::Error::last_os_error();
            if error.kind() == std::io::ErrorKind::AlreadyExists {
                return Err(fail(STATUS_CONFLICT, "atomic target already exists"));
            }
            return Err(fail(STATUS_IO, format!("atomic renameat2 failed: {error}")));
        }
        parent
            .handles
            .0
            .last()
            .unwrap()
            .sync_all()
            .map_err(|error| fail(STATUS_IO, format!("directory fsync failed: {error}")))
    }

    pub(super) fn try_lock(guard: &QfNativeGuard) -> Result<(), i32> {
        fs2::FileExt::try_lock_exclusive(guard.handles.0.last().unwrap())
            .map_err(|error| fail(STATUS_CONFLICT, format!("native lock is busy: {error}")))
    }

    pub(super) fn unlock(guard: &QfNativeGuard) {
        let _ = fs2::FileExt::unlock(guard.handles.0.last().unwrap());
    }
}

#[cfg(not(any(windows, target_os = "linux")))]
mod platform {
    use super::*;

    pub(super) fn directory(_: &Path, _: bool) -> Result<QfNativeGuard, i32> {
        Err(fail(
            STATUS_UNSUPPORTED,
            "native filesystem backend is unavailable",
        ))
    }

    pub(super) fn file(_: &Path, _: u32, _: bool) -> Result<QfNativeGuard, i32> {
        Err(fail(
            STATUS_UNSUPPORTED,
            "native filesystem backend is unavailable",
        ))
    }

    pub(super) fn revalidate(_: &QfNativeGuard) -> Result<QfNativeIdentity, i32> {
        Err(fail(
            STATUS_UNSUPPORTED,
            "native filesystem backend is unavailable",
        ))
    }

    pub(super) fn write_all(_: &QfNativeGuard, _: &[u8]) -> Result<(), i32> {
        Err(fail(
            STATUS_UNSUPPORTED,
            "native staged write is unavailable",
        ))
    }

    pub(super) fn read_all(_: &QfNativeGuard, _: u64) -> Result<Vec<u8>, i32> {
        Err(fail(
            STATUS_UNSUPPORTED,
            "guarded native read is unavailable",
        ))
    }

    pub(super) fn sync_file(_: &QfNativeGuard) -> Result<(), i32> {
        Err(fail(
            STATUS_UNSUPPORTED,
            "native staged flush is unavailable",
        ))
    }

    pub(super) fn publish_noreplace(
        _: &QfNativeGuard,
        _: &QfNativeGuard,
        _: &OsStr,
        _: &OsStr,
    ) -> Result<(), i32> {
        Err(fail(STATUS_UNSUPPORTED, "atomic publish is unavailable"))
    }

    pub(super) fn try_lock(_: &QfNativeGuard) -> Result<(), i32> {
        Err(fail(
            STATUS_UNSUPPORTED,
            "native filesystem backend is unavailable",
        ))
    }

    pub(super) fn unlock(_: &QfNativeGuard) {}
}

#[no_mangle]
/// Opens or creates a directory guard without following unsafe path components.
///
/// # Safety
///
/// `path_utf8` must point to `path_len` readable bytes. `out_guard` must point
/// to writable storage for one guard pointer. A returned guard must eventually
/// be released exactly once with [`qf_native_guard_release`].
pub unsafe extern "C" fn qf_native_guard_directory(
    path_utf8: *const u8,
    path_len: usize,
    create: bool,
    out_guard: *mut *mut QfNativeGuard,
) -> i32 {
    if out_guard.is_null() {
        return fail(STATUS_INVALID_ARGUMENT, "out_guard is required");
    }
    *out_guard = ptr::null_mut();
    let path = match parse_path(path_utf8, path_len) {
        Ok(value) => value,
        Err(code) => return code,
    };
    match platform::directory(&path, create) {
        Ok(guard) => {
            *out_guard = Box::into_raw(Box::new(guard));
            STATUS_OK
        }
        Err(code) => code,
    }
}

#[no_mangle]
/// Opens or exclusively creates a guarded file.
///
/// # Safety
///
/// `path_utf8` must point to `path_len` readable bytes. `out_guard` must point
/// to writable storage for one guard pointer. A returned guard must eventually
/// be released exactly once with [`qf_native_guard_release`].
pub unsafe extern "C" fn qf_native_guard_file(
    path_utf8: *const u8,
    path_len: usize,
    mode: u32,
    require_single_link: bool,
    out_guard: *mut *mut QfNativeGuard,
) -> i32 {
    if out_guard.is_null() {
        return fail(STATUS_INVALID_ARGUMENT, "out_guard is required");
    }
    *out_guard = ptr::null_mut();
    let path = match parse_path(path_utf8, path_len) {
        Ok(value) => value,
        Err(code) => return code,
    };
    match platform::file(&path, mode, require_single_link) {
        Ok(guard) => {
            *out_guard = Box::into_raw(Box::new(guard));
            STATUS_OK
        }
        Err(code) => code,
    }
}

#[no_mangle]
/// Copies the stable identity held by a native guard.
///
/// # Safety
///
/// `guard` must be a live pointer returned by this library. `out_identity`
/// must point to writable storage for one [`QfNativeIdentity`].
pub unsafe extern "C" fn qf_native_guard_identity(
    guard: *const QfNativeGuard,
    out_identity: *mut QfNativeIdentity,
) -> i32 {
    if guard.is_null() || out_identity.is_null() {
        return fail(
            STATUS_INVALID_ARGUMENT,
            "guard and out_identity are required",
        );
    }
    *out_identity = (*guard).identity;
    STATUS_OK
}

#[no_mangle]
/// Copies the guarded path as UTF-8 bytes.
///
/// # Safety
///
/// `guard` must be live and `out_required` must be writable. `buffer` may be
/// null only when `buffer_len` is zero; otherwise it must reference at least
/// `buffer_len` writable bytes.
pub unsafe extern "C" fn qf_native_guard_path(
    guard: *const QfNativeGuard,
    buffer: *mut u8,
    buffer_len: usize,
    out_required: *mut usize,
) -> i32 {
    if guard.is_null() || out_required.is_null() {
        return fail(
            STATUS_INVALID_ARGUMENT,
            "guard and out_required are required",
        );
    }
    let value = (*guard).path.to_string_lossy();
    let bytes = value.as_bytes();
    *out_required = bytes.len();
    if buffer.is_null() || buffer_len < bytes.len() {
        return if buffer.is_null() && buffer_len == 0 {
            STATUS_OK
        } else {
            fail(STATUS_INVALID_ARGUMENT, "path buffer is too small")
        };
    }
    ptr::copy_nonoverlapping(bytes.as_ptr(), buffer, bytes.len());
    STATUS_OK
}

#[no_mangle]
/// Releases a guard returned by this library.
///
/// # Safety
///
/// `guard` must be null or a live pointer returned by this library that has
/// not previously been released. The pointer must not be used afterward.
pub unsafe extern "C" fn qf_native_guard_release(guard: *mut QfNativeGuard) {
    if !guard.is_null() {
        drop(Box::from_raw(guard));
    }
}

#[no_mangle]
/// Copies the current thread's last native error message as UTF-8 bytes.
///
/// # Safety
///
/// `out_required` must be writable. `buffer` may be null only when
/// `buffer_len` is zero; otherwise it must reference at least `buffer_len`
/// writable bytes.
pub unsafe extern "C" fn qf_native_last_error(
    buffer: *mut u8,
    buffer_len: usize,
    out_required: *mut usize,
) -> i32 {
    if out_required.is_null() {
        return STATUS_INVALID_ARGUMENT;
    }
    LAST_ERROR.with(|slot| {
        let value = slot.borrow();
        let bytes = value.as_bytes();
        *out_required = bytes.len();
        if buffer.is_null() || buffer_len < bytes.len() {
            return if buffer.is_null() && buffer_len == 0 {
                STATUS_OK
            } else {
                STATUS_INVALID_ARGUMENT
            };
        }
        ptr::copy_nonoverlapping(bytes.as_ptr(), buffer, bytes.len());
        STATUS_OK
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn temp_root(label: &str) -> PathBuf {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        std::env::temp_dir().join(format!("qf-native-{label}-{}-{nonce}", std::process::id()))
    }

    #[test]
    fn directory_and_exclusive_file_guards_hold_stable_identity() {
        let root = temp_root("guard");
        let directory = platform::directory(&root.join("a").join("b"), true).unwrap();
        assert_ne!(directory.identity.file_id_low, 0);
        let file_path = directory.path.join("project.sqlite");
        let file = platform::file(&file_path, 2, true).unwrap();
        assert_eq!(file.identity.link_count, 1);
        assert!(platform::file(&file_path, 2, true).is_err());
        drop(file);
        drop(directory);
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn guard_revalidation_detects_hard_link_substitution_risk() {
        use std::io::Write;

        let root = temp_root("revalidate");
        let directory = guard_directory(&root, true).unwrap();
        let file_path = directory.path.join("project.sqlite");
        let guard = guard_file(&file_path, FileMode::CreateNew, true).unwrap();
        let mut writer = std::fs::OpenOptions::new()
            .write(true)
            .open(&file_path)
            .unwrap();
        writer.write_all(b"quillframe").unwrap();
        writer.sync_all().unwrap();
        drop(writer);
        assert_eq!(guard.revalidate().unwrap().byte_size, 10);

        let alias = directory.path.join("project-alias.sqlite");
        std::fs::hard_link(&file_path, &alias).unwrap();
        assert!(guard.revalidate().is_err());
        drop(guard);
        drop(directory);
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn project_lock_serializes_cooperating_processes() {
        let root = temp_root("lock");
        let directory = guard_directory(&root, true).unwrap();
        let lock_path = directory.path.join("project.lock");
        let first = QfNativeLock::try_acquire(&lock_path).unwrap();
        assert_eq!(first.path(), lock_path);
        assert!(QfNativeLock::try_acquire(&lock_path).is_err());
        drop(first);
        let second = QfNativeLock::try_acquire(&lock_path).unwrap();
        assert_eq!(second.identity().link_count, 1);
        drop(second);
        drop(directory);
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn unsafe_components_are_rejected_before_io() {
        let root = temp_root("invalid");
        assert!(validate_component(OsStr::new("trailing.")).is_err());
        assert!(validate_component(OsStr::new("stream:name")).is_err());
        #[cfg(windows)]
        assert!(validate_component(OsStr::new("NUL.txt")).is_err());
        assert!(!root.exists());
    }

    #[cfg(windows)]
    #[test]
    fn parent_guard_blocks_rename_until_release() {
        let root = temp_root("rename");
        let guarded = root.join("guarded");
        let guard = platform::directory(&guarded, true).unwrap();
        let renamed = root.join("renamed");
        assert!(std::fs::rename(&guarded, &renamed).is_err());
        drop(guard);
        std::fs::rename(&guarded, &renamed).unwrap();
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn atomic_new_publication_flushes_and_never_replaces() {
        let root = temp_root("atomic-new");
        let directory = guard_directory(&root, true).unwrap();
        let target = root.join("manifest.toml");
        let published =
            atomic_write_new(&target, b"schema = \"quillframe_project_v1_0\"\n").unwrap();
        assert_eq!(
            std::fs::read(&target).unwrap(),
            b"schema = \"quillframe_project_v1_0\"\n"
        );
        assert!(atomic_write_new(&target, b"replacement").is_err());
        assert_eq!(
            std::fs::read(&target).unwrap(),
            b"schema = \"quillframe_project_v1_0\"\n"
        );
        drop(published);
        drop(directory);
        std::fs::remove_dir_all(root).unwrap();
    }

    #[cfg(windows)]
    #[test]
    fn remote_and_verbatim_windows_paths_fail_closed() {
        assert!(validate_lexical_path(Path::new(r"\\server\share\project")).is_err());
        assert!(validate_lexical_path(Path::new(r"\\?\C:\project")).is_err());
    }
}
