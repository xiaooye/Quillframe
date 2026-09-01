FROM rust:1.88-bookworm AS builder
WORKDIR /src
COPY Cargo.toml Cargo.lock rust-toolchain.toml ./
COPY native ./native
COPY persistence ./persistence
COPY studio/host_bridge_contract.json ./studio/host_bridge_contract.json
RUN cargo build --locked --release -p quillframe-host

FROM debian:bookworm-slim
RUN useradd --create-home --uid 10001 quillframe \
    && install -d -o quillframe -g quillframe /srv/quillframe/core
COPY --from=builder /src/target/release/quillframe-host /usr/local/bin/quillframe-host
USER quillframe
WORKDIR /srv/quillframe
ENV QUILLFRAME_CORE_ROOT=/srv/quillframe/core
ENTRYPOINT ["quillframe-host"]
CMD ["stdio", "--core-root", "/srv/quillframe/core"]
