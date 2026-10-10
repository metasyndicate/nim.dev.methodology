# Working Ontology Map

Quick lookup of semantic benchmarks per task or context. Use to map abstract concepts onto
entities, relations, flows, and parameters. Cite the tag when a design decision rests on one.

> Status: URIs below point to canonical project pages/repos and are **unverified** (pending a
> pass to pin raw OWL/JSON URIs and versions). Pin a version when a project depends on one.

| Tag | Scope | Keywords | Source |
|---|---|---|---|
| **BFO** | Top-level foundation. Separates continuants (static entities, parameters, architectures) from occurrents (running processes, methods). Universal rigor. | upper ontology, continuant, occurrent, persistence, boundary | https://github.com/BFO-ontology/BFO |
| **SEON** | Software Engineering Ontology Network. Requirements, design, patterns, coding, configuration management, runtime states, defects. | design process, coding process, configuration management, software artifact | https://nemo.inf.ufes.br/en/projetos/seon/ |
| **SWO** | Software Ontology. Tools, types, tasks, versions, licences, provenance, inputs/outputs, interface types. | CLI utilities, provenance, interface type, data format, execute task | https://github.com/allysonlister/swo |
| **EDAM** | Data analysis and management. Four roots: Topic, Operation, Data, Format. | data life cycle, pipeline, operations, data schema, format | https://github.com/edamontology/edamontology |
| **CDAO** | Comparative Data Analysis Ontology. Evolutionary/hierarchical models: trees, OTUs, character-state transformations. | phylogeny, tree, hierarchy, inheritance, OTU | https://github.com/evoinfo/cdao |

## Companion specifications (validation / modeling)

| Tag | Role | Source |
|---|---|---|
| **SHACL** | Shapes constraints; validates graph data against ontology-aligned shapes | https://www.w3.org/TR/shacl/ |
| **OWL** | Ontology language | https://www.w3.org/TR/owl2-overview/ |
| **JSON Schema** | Config/API/data validation at `loose`/`standard` rigor | https://json-schema.org/ |
| **OpenAPI** | HTTP API spec layer | https://spec.openapis.org/oas/latest.html |
| **LinkML** | Language-agnostic metamodel; generates OWL, JSON Schema, SQL DDL, pydantic | https://github.com/linkml/linkml |

## Libraries to search for others

OBO Foundry (obofoundry.org), Protege Ontology Library, COLORE, OMG Commons Ontology Library.

## Usage

1. Identify the concept (e.g., "a CLI tool and its parameters").
2. Look up the nearest tag(s) by keyword; read the relevant class/relation names.
3. Align schema names to the benchmark where sensible, or record the deviation and why.
