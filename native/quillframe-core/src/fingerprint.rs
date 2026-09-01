use std::fmt::Write;

use sha2::{Digest, Sha256};

pub(crate) fn sha256_fingerprint(bytes: impl AsRef<[u8]>) -> String {
    let digest = Sha256::digest(bytes.as_ref());
    let mut value = String::with_capacity("sha256:".len() + digest.len() * 2);
    value.push_str("sha256:");
    for byte in digest {
        write!(&mut value, "{byte:02x}").expect("writing to a String cannot fail");
    }
    value
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn fingerprint_is_canonical_sha256() {
        assert_eq!(
            sha256_fingerprint(b"quillframe"),
            "sha256:daf80b110b8b08483649166b315e94a18af64faa61f5904cb9c9868aacfd830a"
        );
    }
}
