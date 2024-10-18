# SBOM-Meta

An example Chai application that displays package metadata for
[SBOMs](https://github.com/anchore/syft) (software bill of materials).

## Installation

1. Start the [Chai DB](https://github.com/teaxyz/chai-oss) with `docker compose up`.
2. Run `go install` or `go build` to generate a binary.

## Usage

Run `sbom-meta` in the root directory of any repository to get a list of
dependencies with metadata.

```bash
git clone git@github.com:starship/starship.git
cd starship
sbom-meta
```

You can sort any of the fields, ascending or descending:

```bash
sbom-meta --sort downloads,desc
sbom-meta --sort published,asc
```

Use the `--json` flag to output JSON:

```bash
sbom-meta --json | jq .[1].name
```
