# Install `mosaicod`

The `mosaicod` daemon acts as the central hub of the platform. Written in Rust for performance and safety, it handles the heavy lifting of data ingestion, conversion, compression, and organized storage. It exposes a [Flight-based API](https://arrow.apache.org/docs/format/Flight.html) that the client SDK interact with.

## Quick Start

For rapid prototyping, we provide a Docker Compose configuration. This sets up a volatile environment that includes both the Mosaico server and a PostgreSQL database.

```bash
# Navigate to the quick start directory form the root folder
cd docker/quick_start
# Startup the infra in background
docker compose up -d
```
This launches PostgreSQL on port `5432` and `mosaicod` on its **default port** `6726`

!!! note "Note"

    The default Mosaico configuration uses non persistent storage. This means that if the container is destroyed, all stored data will be lost. Since Mosaico is still under active development, we provide this simple, volatile setup by default. For persistent storage, the standard compose.yml file can be easily extended to utilize a Docker volume.


## Building from Source

To build Mosaico for production, you need a Rust toolchain. Mosaico uses `sqlx` for compile-time query verification, which typically requires a live database connection. However, we support an offline build mode using cached metadata.

**Option A: Offline Build (Recommended)**

```bash
SQLX_OFFLINE=true cargo build --release

```

The binary will be located at `target/release/mosaicod`.

**Option B: Live Migrations**
If you are modifying the database schema:

1. Install SQLx CLI: `cargo install sqlx-cli`
2. Configure `.env`: `DATABASE_URL=postgres://user:pass@localhost:5432/mosaico`
3. Run migrations: `cargo sqlx migrate run`
4. Build: `cargo build --release`

## Configuration

The server supports local filesystem storage by default but can be configured for S3-compatible remote storage via environment variables.

**Basic Local Storage:**

```bash
./mosaicod run --local-store /var/lib/mosaico/data

```

**S3 Remote Storage Variables:**

* `MOSAICO_STORE_BUCKET`: Bucket name.
* `MOSAICO_STORE_ENDPOINT`: Object storage URL.
* `MOSAICO_STORE_ACCESS_KEY`: Public key.
* `MOSAICO_STORE_SECRET_KEY`: Secret key.
