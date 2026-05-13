# Architecture Diagram — avm-metadata Workflows

```mermaid
flowchart LR
    classDef operator fill:#1a6bb5,stroke:#0d4a8a,color:#fff,font-weight:bold
    classDef assistant fill:#c0392b,stroke:#922b21,color:#fff,font-weight:bold
    classDef script fill:#1e8449,stroke:#145a32,color:#fff,font-weight:bold
    classDef data fill:#555f6b,stroke:#3d464f,color:#fff

    subgraph OP["OPERATOR · avm.sh / avm.ps1"]
        direction TB
        OP_SETUP["avm setup"]:::operator
        OP_CLONE["avm clone"]:::operator
        OP_UPDATE["avm update"]:::operator
        OP_FETCH["avm fetch"]:::operator
        OP_STATUS["avm status"]:::operator
        OP_CLEANUP["avm cleanup"]:::operator
        OP_BRANCH["avm branch"]:::operator
        OP_STASH["avm stash"]:::operator
        OP_RESET["avm reset"]:::operator
        OP_RUN["avm run"]:::operator
        OP_SYNC["avm sync"]:::operator
        OP_SCRAPE["avm scrape"]:::operator
        OP_CHECK["avm check"]:::operator
    end

    subgraph SCRIPTS["scripts/  ·  Shared Automation Layer"]
        direction TB
        SC_GEN["generate_config.py\n"]:::script
        SC_REPOS["manage_repos.py\n"]:::script
        SC_SYNC["sync_catalog.py\n"]:::script
        SC_ANALYZE["analyze_module.py\n"]:::script
    end

    subgraph AS["ASSISTANT · Copilot Chat / CLI"]
        direction TB
        AS_SYNC["/avm-sync\n"]:::assistant
        AS_CHECK["/avm-check\n"]:::assistant
    end

    OP_SETUP --> SC_GEN
    OP_CLONE & OP_UPDATE & OP_FETCH & OP_STATUS & OP_CLEANUP & OP_BRANCH & OP_STASH & OP_RESET & OP_RUN -->|invokes| SC_REPOS
    OP_SYNC -->|invokes| SC_SYNC
    OP_SCRAPE & OP_CHECK --> SC_ANALYZE

    AS_SYNC -->|invokes| SC_SYNC
    AS_CHECK --> SC_REPOS
    AS_CHECK -->|invokes| SC_ANALYZE

    style OP fill:#dbeafe,stroke:#1a6bb5,stroke-width:2px,color:#0d4a8a,rx:12
    style SCRIPTS fill:#dcfce7,stroke:#1e8449,stroke-width:2px,color:#145a32,rx:12
    style AS fill:#fee2e2,stroke:#c0392b,stroke-width:2px,color:#922b21,rx:12

    DATA_MODULES["data/modules/*.yaml\nmodule catalog — source of truth"]:::data
    CONFIG_YAML[".config/modules.yaml\ngenerated — gitignored"]:::data
    CLONED["terraform-azurerm-avm-*/\ncloned module repos — gitignored"]:::data

    SC_GEN -.->|reads| DATA_MODULES
    SC_GEN ==>|writes| CONFIG_YAML
    SC_SYNC ==>|writes| DATA_MODULES
    SC_ANALYZE ==>|writes| DATA_MODULES
    SC_REPOS -.->|reads| CONFIG_YAML
    SC_REPOS ==>|writes| CLONED
```

> **Color key:**
> - **Blue** — Operator entry point and commands (`avm.sh` / `avm.ps1`)
> - **Red** — Assistant entry point (Copilot chat skills)
> - **Green** — Shared `scripts/` automation layer
> - **Grey** — Data / output layer (files and directories)

> **Edge key:**
> - Solid arrow `-->` — invokes
> - Thick arrow `==>` — writes
> - Dashed arrow `-.->` — reads
