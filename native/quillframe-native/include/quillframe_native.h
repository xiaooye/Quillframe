#ifndef QUILLFRAME_NATIVE_H
#define QUILLFRAME_NATIVE_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct QfNativeGuard QfNativeGuard;

typedef struct QfNativeIdentity {
  uint64_t volume_id;
  uint64_t file_id_low;
  uint64_t file_id_high;
  uint64_t link_count;
  uint64_t byte_size;
  uint32_t attributes;
  uint32_t reparse_tag;
} QfNativeIdentity;

enum QfNativeFileMode {
  QF_FILE_OPEN_READ = 0,
  QF_FILE_OPEN_READ_WRITE = 1,
  QF_FILE_CREATE_NEW = 2,
  QF_FILE_OPEN_OR_CREATE = 3
};

int32_t qf_native_guard_directory(
    const uint8_t *path_utf8,
    size_t path_len,
    bool create,
    QfNativeGuard **out_guard);

int32_t qf_native_guard_file(
    const uint8_t *path_utf8,
    size_t path_len,
    uint32_t mode,
    bool require_single_link,
    QfNativeGuard **out_guard);

int32_t qf_native_guard_identity(
    const QfNativeGuard *guard,
    QfNativeIdentity *out_identity);

int32_t qf_native_guard_path(
    const QfNativeGuard *guard,
    uint8_t *buffer,
    size_t buffer_len,
    size_t *out_required);

void qf_native_guard_release(QfNativeGuard *guard);

int32_t qf_native_last_error(
    uint8_t *buffer,
    size_t buffer_len,
    size_t *out_required);

#ifdef __cplusplus
}
#endif

#endif

