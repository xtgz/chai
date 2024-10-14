# SBOM-Meta

An example Chai application that displays package metadata for
[SBOMs](https://github.com/anchore/syft) (software bill of materials).

## Installation

1. Start the [Chai DB](https://github.com/teaxyz/chai-oss) with `docker compose up`.
2. Run `go install` or `go build` to generate a binary.

## Usage

From the root directory of any repository run `sbom-meta`, you can also specify
a source with `sbom-meta SOURCE` for any of the [supported sources](https://github.com/anchore/syft/wiki/supported-sources),
including Docker images. Use the `--json` flag to omit JSON.
