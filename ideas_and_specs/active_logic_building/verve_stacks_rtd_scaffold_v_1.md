# VerveStacks ReadTheDocs Scaffold (v1)

Below is a complete starter structure for an RTD site, with **landing page copy** embedded in `index.rst` (including the Open‑Use vision, precise offering, and expectations). You can copy this into a `docs/` folder and build with Sphinx.

---

## Project tree

```text
docs/
  conf.py                # (optional here; add later if needed)
  index.rst              # Landing page with Open‑Use vision & offering
  getting-started/
    quickstart.rst
    outputs.rst
    faq.rst
  model-library/
    index.rst
    iso-template.rst
  using/
    web-ui.rst
    scenarios.rst
    exports.rst
  data-assumptions/
    index.rst
    sources.rst
    costs.rst
    fuel-prices-policies.rst
    calibration.rst
    limitations.rst
  methods/
    timeslice-stress.rst
    rez-gapfilling.rst
    storage-adequacy.rst
    retrofit-ccs.rst
    transmission-rez.rst
    emulator.rst
  integration/
    times.rst
    osemosys.rst
    pypsa.rst
    leap.rst
    formats.rst
  tutorials/
    beginner.rst
    intermediate.rst
    advanced.rst
  community/
    roadmap.rst
    publications.rst
    partners.rst
    support.rst
  reference/
    glossary.rst
    parameters.rst
    changelog.rst
    license.rst
    citation.rst
```

---

## docs/index.rst

```rst
.. title:: VerveStacks — Open‑Use Energy Modeling

=============================================
VerveStacks — Open‑Use Energy Modeling
=============================================

**Energy system modeling — reimagined for use.**

Most modeling projects begin by building the model. VerveStacks begins where others stop — with
**ready‑to‑use, decision‑grade power‑sector models** you can explore immediately. We call this
**open‑use**: models and assumptions are open to *use, inspect, and question*; pipelines may remain
managed so quality can scale. The emphasis is on **results and interpretation**, not on forcing every
user to become a model builder.

Open‑Use vision
---------------

- **Liberate the user.** Many domain experts are *too deep in reality* to spend months building
  infrastructure just to test a question. VerveStacks brings them in — policymakers, consultants,
  planners, analysts, and teachers who want trustworthy, transparent models they can run today.
- **Managed complexity.** Proprietary tools hide complexity; open‑source can expose it raw. VerveStacks
  makes complexity *usable* — transparent data, explicit methods, and practical defaults that travel
  well across contexts.
- **Use over build.** We separate the craft of building pipelines from the skill of using models. The
  latter is where decisions live. VerveStacks exists to create a **new class of modelers — expert users**
  who ask better questions, run scenarios fast, and interpret results with confidence.

What you get (the offering)
---------------------------

- **Model Library**: high‑resolution, per‑ISO power‑sector models with transparent assumptions, versioned
  model cards, and known‑gap notes.
- **Immediate exploration in Veda Online (VO)**: run scenarios, compare results, and share insight without
  setup.
- **Scenario templates**: sensible defaults for common analyses (policy toggles, cost sensitivities,
  demand variants, climate categories).
- **Interoperable exports**: artifacts for TIMES, OSeMOSYS, PyPSA, LEAP; plus CSV/Excel for audit and
  reporting.
- **Methods & data transparency**: clear documentation of time‑slice design, renewable gap‑filling,
  storage/adequacy treatment, retrofit logic, transmission/REZ mapping, data sources, and calibration.

Expectations & ethos
--------------------

- **A new class of modelers**: We expect many users who never touched ESOMs to become *model users* —
  “story‑builders” who shape scenarios and interpret trade‑offs without becoming pipeline engineers.
- **Versioned, decision‑grade artifacts**: every release is pinned, cited, and never overwritten.
- **Open improvement loop**: challenge our assumptions; propose better ones; we’ll regenerate and version
  results. *Quality grows through use.*

Get started
-----------

- :doc:`/model-library/index` — browse available ISOs and read model cards.
- :doc:`/getting-started/quickstart` — run your first scenario in minutes.
- :doc:`/data-assumptions/index` — understand sources, vintages, and limitations.
- :doc:`/methods/timeslice-stress` — how our time‑slice/stress methodology works.

.. toctree::
   :maxdepth: 2
   :caption: Navigate

   getting-started/quickstart
   getting-started/outputs
   getting-started/faq
   model-library/index
   data-assumptions/index
   methods/timeslice-stress
   methods/rez-gapfilling
   using/web-ui
   integration/formats
   tutorials/beginner
   community/roadmap
   reference/license
```

---

## docs/getting-started/quickstart.rst

```rst
============================
Quickstart: Run a Scenario
============================

This five‑minute guide shows how to pick an ISO model, launch a scenario in Veda Online (VO),
and view the key outputs.

1. **Pick a model**: open the :doc:`/model-library/index` and select an ISO.
2. **Open in VO**: click *Explore in VO* on the model card.
3. **Choose a scenario**: start with a baseline template, then toggle a policy or cost sensitivity.
4. **Run & compare**: execute the run and compare with the baseline using the Results viewer.
5. **Export**: download CSV/Excel artifacts or an interoperable bundle (TIMES/OSeMOSYS/PyPSA/LEAP).

.. note::
   New to VO? See :doc:`/using/web-ui` and :doc:`/getting-started/outputs`.
```

## docs/getting-started/outputs.rst

```rst
========================
Understanding the Outputs
========================

The Results viewer organizes outputs into **capacity**, **generation**, **emissions**, **cost**, and
**adequacy/storage**. Use the *Compare* mode to view deltas between scenarios. Export any chart’s data
as CSV/Excel for audit and reporting.
```

## docs/getting-started/faq.rst

```rst
===
FAQ
===

**Is VerveStacks open‑source?**
  VerveStacks is **open‑use**: the models, assumptions, and methods are documented and free to use;
  pipelines may be managed to preserve quality and velocity.

**Can I request a new ISO?**
  Yes — see :doc:`/community/support`.

**Can I modify and redistribute a model?**
  See :doc:`/reference/license` for allowed uses and attribution.
```

---

## docs/model-library/index.rst

```rst
=============
Model Library
=============

Browse available ISO models. Each model card includes intended use, coverage, assumptions, known gaps,
version, and citation.

.. note::
   Start with the :doc:`iso-template` to understand the structure of a model card.

.. toctree::
   :maxdepth: 1

   iso-template
```

## docs/model-library/iso-template.rst

```rst
=============================
Model Card — <ISO Code/Name>
=============================

**Intended use**
  Who should use this model and for what kinds of questions.

**Coverage**
  Years, temporal resolution, technologies, regions/zones, interconnections.

**Data & assumptions**
  Major sources and vintages; links to :doc:`/data-assumptions/index` for full details.

**Calibration & validation**
  Benchmarks used; notable discrepancies and their rationale.

**Known gaps & limitations**
  What to treat cautiously; planned improvements.

**Version**
  Model version, release date, checksum/ID.

**How to cite**
  See :doc:`/reference/citation`.

**Explore in VO**
  Link or button to open this model in Veda Online.
```

---

## docs/using/web-ui.rst

```rst
======================
Using the Web Interface
======================

A quick tour of VO: model selector, scenario panel, run queue, and Results viewer. Keyboard shortcuts,
compare mode, and saving/sharing views.
```

## docs/using/scenarios.rst

```rst
=================
Working Scenarios
=================

Scenario templates (policy toggles, cost sensitivities, demand variants), naming conventions, and best
practices for comparisons.
```

## docs/using/exports.rst

```rst
==================
Exports & Bundles
==================

How to export CSV/Excel artifacts and interoperable bundles for TIMES, OSeMOSYS, PyPSA, and LEAP.
```

---

## docs/data-assumptions/index.rst

```rst
===================
Data & Assumptions
===================

Provenance, vintages, and selection logic for all data and assumptions. See subpages for details.

.. toctree::
   :maxdepth: 1

   sources
   costs
   fuel-prices-policies
   calibration
   limitations
```

## docs/data-assumptions/sources.rst

```rst
===============
Source Datasets
===============

List major datasets and vintages. Describe selection criteria and known caveats.
```

## docs/data-assumptions/costs.rst

```rst
============================
Technology Costs & Settings
============================

Document cost/performance assumptions (with citations) and how they map into each framework.
```

## docs/data-assumptions/fuel-prices-policies.rst

```rst
==========================
Fuel Prices & Key Policies
==========================

Fuel price trajectories and policy constraints; scenario‑specific toggles link to :doc:`/using/scenarios`.
```

## docs/data-assumptions/calibration.rst

```rst
======================
Calibration & Checks
======================

Benchmarks and sanity checks; reconciliation notes by ISO.
```

## docs/data-assumptions/limitations.rst

```rst
===========================
Limitations & Known Gaps
===========================

What to treat cautiously; implications for interpretation; planned improvements.
```

---

## docs/methods/timeslice-stress.rst

```rst
=====================================
Time‑Slice Design & Stress Selection
=====================================

How VerveStacks selects stress periods and constructs time slices from hourly data; validation logic and
implications for adequacy and storage.
```

## docs/methods/rez-gapfilling.rst

```rst
========================================
Renewables: REZ Mapping & Gap‑Filling
========================================

RE potential characterization, spatial aggregation, and the gap‑filling approach that preserves totals
*and* spatial intelligence.
```

## docs/methods/storage-adequacy.rst

```rst
========================
Storage & Adequacy Logic
========================

Representation of storage types, adequacy metrics, and how stress periods capture operational risk.
```

## docs/methods/retrofit-ccs.rst

```rst
=====================
Retrofit & CCS Paths
=====================

Thermal fleet life‑extension, retrofit options, and CCS configurations.
```

## docs/methods/transmission-rez.rst

```rst
=================================
Transmission & REZ Integration
=================================

How REZs connect to nodes, treatment of transmission costs and constraints.
```

## docs/methods/emulator.rst

```rst
=====================
Emulator (Roadmap)
=====================

A high‑level preview of the conversational/emulator layer — what it will do, how it is trained, and
reliability gates back to full model runs.
```

---

## docs/integration/times.rst

```rst
=================
Using with TIMES
=================

Mapping tables, file structures, and caveats for TIMES users.
```

## docs/integration/osemosys.rst

```rst
=====================
Using with OSeMOSYS
=====================

How to import VS artifacts; structural notes and limitations.
```


## docs/integration/formats.rst

```rst
===================
File Formats & APIs
===================

Schemas and conventions for CSV/Excel exports and VO bundles; versioning and checksums.
```

---

## docs/tutorials/beginner.rst

```rst
=====================
Beginner Tutorials
=====================

Guided exercises for first‑time users: choose a model, toggle a policy, compare scenarios, export results.
```

## docs/tutorials/intermediate.rst

```rst
========================
Intermediate Tutorials
========================

Demand variants, cost sensitivities, and multi‑ISO comparisons.
```

## docs/tutorials/advanced.rst

```rst
=====================
Advanced Tutorials
=====================

Designing policy bundles, stress‑testing adequacy, and triaging transmission upgrades.
```

---

## docs/community/roadmap.rst

```rst
=======
Roadmap
=======

Upcoming ISOs, features, and publications. Invite feedback and collaborator interest.
```

## docs/community/publications.rst

```rst
============
Publications
============

Papers, presentations, and citations relevant to VerveStacks.
```

## docs/community/partners.rst

```rst
========
Partners
========

Consultants, institutions, and collaborators who use or contribute to VerveStacks.
```

## docs/community/support.rst

```rst
=======
Support
=======

How to get help, request a new ISO, or suggest improved assumptions.
```

---

## docs/reference/glossary.rst

```rst
========
Glossary
========

Acronyms and key terms used across the docs.
```

## docs/reference/parameters.rst

```rst
==========
Parameters
==========

Reference list of parameters and their meaning across frameworks.
```

## docs/reference/changelog.rst

```rst
=========
Changelog
=========

Versioned releases with highlights and checksums.
```

## docs/reference/license.rst

```rst
=====================
Open‑Use License (Draft)
=====================

**Free to use** the published models, assumptions, and documentation for research, policy analysis,
consulting, teaching, and journalism, with attribution.

**Allowed**: running scenarios, publishing results/figures with citation, and creating derivative
analyses that reference the specific VerveStacks version used.

**Managed**: pipelines and regeneration services may remain proprietary to protect quality and velocity.

**Attribution**: cite the model card, version ID, and VerveStacks. See :doc:`/reference/citation`.
```

## docs/reference/citation.rst

```rst
========
Citation
========

*VerveStacks, Version X.Y (ISO: <name>), release <YYYY‑MM‑DD>. VerveStacks Open‑Use models. URL: <docs URL>*

Include the model card link and checksum/ID when available.
```

