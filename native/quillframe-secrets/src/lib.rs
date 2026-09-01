use quillframe_core::{CoreError, CoreResult, SecretStore};

const SERVICE: &str = "com.quillframe.studio";
const PREFIX: &str = "keyring:qf:";

#[derive(Clone, Copy, Debug, Default)]
pub struct OsSecretStore;

impl SecretStore for OsSecretStore {
    fn read_secret(&self, credential_ref: &str) -> CoreResult<Option<String>> {
        let entry = entry(credential_ref)?;
        match entry.get_password() {
            Ok(secret) => Ok(Some(secret)),
            Err(keyring::Error::NoEntry) => Ok(None),
            Err(error) => Err(secret_error(error)),
        }
    }

    fn write_secret(&self, credential_ref: &str, secret: &str) -> CoreResult<()> {
        if secret.is_empty() {
            return Err(CoreError::ModelRuntime("secret cannot be empty".into()));
        }
        entry(credential_ref)?
            .set_password(secret)
            .map_err(secret_error)
    }

    fn delete_secret(&self, credential_ref: &str) -> CoreResult<()> {
        match entry(credential_ref)?.delete_credential() {
            Ok(()) | Err(keyring::Error::NoEntry) => Ok(()),
            Err(error) => Err(secret_error(error)),
        }
    }
}

pub fn credential_ref(service_id: &str) -> CoreResult<String> {
    if service_id.is_empty()
        || service_id.len() > 128
        || !service_id
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'-' | b'_'))
    {
        return Err(CoreError::ModelRuntime(
            "service id is not canonical for an OS credential reference".into(),
        ));
    }
    Ok(format!("{PREFIX}{service_id}"))
}

fn entry(credential_ref: &str) -> CoreResult<keyring::Entry> {
    let account = credential_ref
        .strip_prefix(PREFIX)
        .filter(|value| {
            !value.is_empty()
                && value.len() <= 128
                && value
                    .bytes()
                    .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'-' | b'_'))
        })
        .ok_or_else(|| {
            CoreError::ModelRuntime("credential reference is not a Quillframe keyring ref".into())
        })?;
    keyring::Entry::new(SERVICE, account).map_err(secret_error)
}

fn secret_error(error: keyring::Error) -> CoreError {
    CoreError::ModelRuntime(format!("OS credential store failed: {error}"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn credential_references_are_non_secret_and_canonical() {
        assert_eq!(
            credential_ref("service_01").unwrap(),
            "keyring:qf:service_01"
        );
        assert!(credential_ref("../bad").is_err());
    }
}
