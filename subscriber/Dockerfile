FROM rust:1.68-buster

RUN apt-get update && \
    apt-get -y install git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    rustup component add rls rust-analysis rust-src rustfmt clippy && \
    cargo install cargo-edit cargo-watch

WORKDIR /var/subscriber
COPY subscriber/Cargo.toml ./

# Build the dependencies first to cache them
RUN mkdir src && \
    echo "fn main() {}" > src/main.rs && \
    cargo build --release && \
    rm -f target/release/deps/subscriber*

COPY . .

RUN cargo build --release
