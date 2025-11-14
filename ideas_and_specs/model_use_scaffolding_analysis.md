# The Model Use Scaffolding Gap: FACETS BAU Analysis as a Case Study

**Date**: October 25, 2025  
**Context**: Analysis of FACETS BAU factorial design vs traditional 3-scenario approach

## Executive Summary

The energy modeling field has focused intensively on building sophisticated models but has neglected developing the scaffolding required to USE them appropriately. The FACETS BAU analysis (March 2025) demonstrates what proper model use looks like - and reveals why it remains rare even among capable modeling teams.

## Traditional Approach: The "3 Scenarios" Paradigm

Most energy modeling studies follow a simple pattern:
- **Reference/BAU**: Business as usual continuation
- **Policy**: Moderate intervention scenario  
- **Deep Decarbonization**: Aggressive climate policy

**Example**: "We ran three scenarios to explore the range of outcomes"

**Limitations of this approach**:
- Cannot identify which factors drive outcomes (gas prices? RE costs? policy design?)
- No systematic exploration of interaction effects
- Single point estimates mask enormous uncertainty ranges
- Cannot answer "what drives the difference between scenarios?"
- Risk of cherry-picking scenarios that confirm priors

## FACETS BAU Approach: Factorial Scenario Design

The FACETS analysis systematically explores the scenario space across **6 dimensions**:

### Scenario Structure
```
Dimension               | Options | Code
------------------------|---------|------------------
Gas Price              | 3       | gp-Low/Inter/High
RE Costs               | 3       | re-Low/Inter/High  
Electricity Demand     | 2       | dm-Low/High
Policy Mix             | 4       | Pol-All/IRA/Part/Void
Transmission/RE Builds | 2       | Xm-M/R
Carbon Cap             | 2       | Cp-00/95
```

### Total Scenario Universe
**Base combinations**: 3 × 3 × 2 × 4 × 2 × 2 = **288 scenarios**

In practice, FACETS appears to have run a strategic subset focusing on key combinations, but the framework enables systematic exploration.

### What This Enables

**1. Driver Attribution**
- "RE costs are a bigger driver of long-term emissions than gas prices when demand is Low" (Slide 14)
- "Low gas prices drive higher long-term emissions especially when IRA RE incentives are not available" (Slide 15)
- These insights are IMPOSSIBLE with 3 scenarios

**2. Interaction Effects**
- Build restrictions make a bigger difference when RE costs are Low or Intermediate (Slide 13)
- IRA effectiveness depends on RE cost competitiveness (Slide 28)
- Policy impacts vary dramatically with demand levels (Slides 12-13)

**3. Risk Assessment**
- "High demand growth poses a strong risk of renewed emissions growth" (Slide 26)
- Quantified range: emissions can fall to below 95% target OR rise to 2015 levels
- Traditional 3-scenario approach would miss this bifurcation

**4. Robust Insights**
- "Wind becomes the largest generation source in ALL scenarios" (Slide 18)
- This finding holds across 100+ scenario combinations - gives confidence
- With 3 scenarios, you can't distinguish robust trends from scenario artifacts

**5. Policy Design Intelligence**
- "CCS development is highly dependent on 45Q incentives" - no CCS in Void cases, limited even with cap (Slides 22, 27)
- "IRA RE incentives reduce carbon price from $100/ton to $45/ton" (Slide 23)
- Enables evidence-based policy package design

## The Scaffolding Gap: Why This Approach Remains Rare

Despite having capable models (FACETS, TIMES, GCAM, etc.), most studies run 3-10 scenarios. Why?

### Missing Infrastructure

**1. Scenario Management**
- No standard tools for factorial design specification
- No naming conventions (FACETS uses `gp-X.re-X.dm-X.Pol-X.Xm-X.Cp-X`)
- No frameworks for scenario dependency management

**2. Batch Execution**
- Models weren't designed for 100+ automated runs
- No standard queue management or failure recovery
- No compute infrastructure guidance (cloud vs local)

**3. Results Management**
- Output files for 288 scenarios = massive data management challenge
- No standard post-processing pipelines
- No version control practices for scenario results

**4. Analysis Tools**
- Visualization tools designed for 3-line comparisons, not 288
- No frameworks for driver attribution analysis
- No standard methods for interaction effect identification
- Slide 11-15 charts (emissions by various groupings) require custom tools

**5. Communication Methods**
- Traditional reports expect 3 scenarios max
- No visualization standards for multidimensional scenario spaces
- Stakeholders not trained to interpret factorial analyses

### Time and Cost Barriers

**Traditional 3-scenario study**:
- Model setup: 1-2 months
- 3 scenario runs: 1-3 days
- Analysis: 1-2 weeks
- **Total: 2-3 months**

**FACETS factorial approach**:
- Model setup: 1-2 months (same)
- **Scenario design**: 1-2 weeks (NEW requirement)
- 100+ scenario runs: 1-2 weeks with proper infrastructure
- **Results management**: 1-2 weeks (NEW requirement)  
- **Multidimensional analysis**: 3-4 weeks (vs 1-2 weeks)
- **Total: 3-4 months**

The incremental time is manageable WITH proper scaffolding, prohibitive WITHOUT it.

### Skill Gap

This approach requires different skills:
- **Design of Experiments** thinking (factorial design)
- **Data science** skills (managing 100+ result sets)
- **Visual analytics** (multidimensional data exploration)
- **Statistical thinking** (driver attribution, interaction effects)

These skills are uncommon in energy modeling teams trained primarily in engineering and economics.

## What FACETS Got Right

The presentation reveals sophisticated scaffolding:

**1. Systematic naming convention**
- `gp-X.re-X.dm-X.Pol-X.Xm-X.Cp-X` enables programmatic filtering
- Each dimension independently queryable

**2. Thoughtful scenario grouping**
- Slides 11-20: Multiple views of same data by different groupings
- "by demand scenario", "by Gas price-RE scenario", "by Policy-Builds"
- Shows understanding that different audiences need different views

**3. Layered analysis structure**
- First: Overall patterns (Slide 11)
- Then: By major dimension (demand) (Slides 12-13)
- Then: By interaction effects (Slides 14-15)
- Finally: Technology details (Slides 16-22)

**4. Synthetic insights**
- "Competition between RE and gas has replaced gas-coal competition" (Slide 26)
- This emerges FROM the systematic exploration, not assumed beforehand

**5. Cost of decarbonization analysis**
- Slides 23-25: Carbon prices and electricity costs across scenarios
- Reveals how IRA, demand, and build restrictions affect costs
- Impossible to derive from 3 scenarios

## The Case for "Use Scaffolding" Investment

### Current State
Energy modeling field has invested heavily in:
- Model frameworks (TIMES, MESSAGE, GCAM, WITCH, etc.)
- Global databases (IEA, IRENA, EMBER, etc.)
- Computing power (cloud, HPC clusters)

**But has NOT invested in**:
- Scenario design frameworks
- Batch execution infrastructure  
- Results management systems
- Multidimensional analysis tools
- Communication methods for complex scenario spaces

### The Consequence
Even sophisticated modeling teams with capable models typically:
- Run 3-5 scenarios per study
- Cannot systematically attribute drivers
- Miss interaction effects
- Provide single-point estimates masking huge uncertainties
- Cannot provide robust policy guidance

**The modeling capability exists. The USE capability doesn't.**

### What's Needed

**1. Scenario Design Tools**
- Factorial design templates for energy models
- Sensitivity analysis frameworks
- Scenario space visualization tools

**2. Execution Infrastructure**  
- Batch processing frameworks (like VerveStacks batch_process_models.py)
- Cloud deployment patterns
- Result provenance tracking

**3. Analysis Frameworks**
- Standard post-processing pipelines
- Driver attribution methods
- Interaction effect identification tools
- Multidimensional visualization libraries

**4. Communication Templates**
- Reporting structures for factorial analyses
- Visualization standards (like FACETS Slides 11-25)
- Stakeholder communication guidance

**5. Training and Methods**
- Design of Experiments for energy modeling
- Multidimensional analysis techniques
- Visual analytics for scenario spaces

## Connection to VerveStacks Vision

VerveStacks addresses the MODEL BUILDING bottleneck:
- "190+ country models in minutes instead of months"
- Automated data integration and version control
- Democratized model access

**But this FACETS analysis reveals the next frontier**: MODEL USE scaffolding

Even with free access to 190+ VerveStacks models, users face the same challenges:
- How to design meaningful scenario spaces?
- How to run and manage 100+ scenarios?
- How to analyze and communicate multidimensional results?

**The Open Use movement needs both**:
1. ✅ Model access (VerveStacks solves this)
2. ⚠️ Use scaffolding (largely unsolved)

### Opportunity

"Democratizing energy modeling" means:
- **Not just**: Giving people models
- **But also**: Giving them the scaffolding to use models appropriately

This could be transformative for:
- **Developing countries**: Access to proper scenario analysis without advanced modeling teams
- **Policy makers**: Better decision support from systematic exploration
- **Academic researchers**: Higher quality analysis with less manual effort
- **Private sector**: Faster, more rigorous strategic planning

## Quantifying the Impact

### FACETS BAU Analysis Insights vs Traditional 3-Scenario Approach

**Traditional approach might conclude**:
- "Emissions fall 60% by 2050 under Reference policies"
- "Deep decarbonization requires aggressive policy intervention"
- "Wind and solar dominate future generation mix"

**FACETS factorial approach reveals**:
- Emissions range from 95% reduction to ABOVE 2023 levels depending on demand/policy/costs
- RE-gas competition is the PRIMARY driver (not policy alone)
- IRA incentives reduce carbon price from $100/ton to $45/ton (8-year payback on incentive investment if SCC = $100/ton)
- Build restrictions increase costs significantly in high demand scenarios
- CCS only viable with 45Q incentives
- Wind dominance is ROBUST (holds across all scenarios), giving confidence

**The difference**: Actionable insights for policy design vs generic directional guidance

### Efficiency Gains from Proper Scaffolding

Current state (estimated):
- 100 scenario analysis: 4-6 months manual effort, requires expert team
- Result: Rare, expensive, limited to well-funded projects

With proper scaffolding:
- 100 scenario analysis: 4-6 weeks with standard tools, accessible to broader teams
- Result: Becomes standard practice, like statistical analysis in other fields

**10x productivity gain** enabling:
- More frequent scenario updates
- Broader scenario exploration  
- Smaller teams doing sophisticated work
- Developing countries accessing same quality analysis

## Conclusion

The energy modeling field has created impressive models but has NEGLECTED the infrastructure required to use them appropriately. The FACETS BAU analysis demonstrates what proper use looks like - but reveals how rare and difficult it remains.

**The path forward requires investment in**:
- Scenario design frameworks and tools
- Batch execution and results management infrastructure
- Multidimensional analysis and visualization capabilities  
- Training in Design of Experiments and visual analytics
- Communication methods for complex scenario spaces

This "use scaffolding" is as important as model development itself. Without it, even the best models will continue to be underutilized, providing suboptimal guidance to critical energy transition decisions.

**The bottleneck isn't model capability - it's use capability.**

---

## Appendix: FACETS Presentation Structure Analysis

The 47-slide presentation follows a sophisticated structure:

**Setup (Slides 1-9)**:
- Scenario dimensions and options
- Input assumptions (gas prices, RE costs, demand)
- Build restrictions and policy details

**Emissions Analysis (Slides 10-15)**:
- Overall patterns, then by demand, then by interactions
- Systematic decomposition of drivers

**Technology Mix (Slides 16-22)**:
- Evolution over time (2030, 2035, 2050)
- By scenario dimensions
- Specific technologies (wind, CCS)

**Economics (Slides 23-25)**:
- Carbon prices
- Electricity costs
- By scenario dimensions

**Synthesis (Slides 26-29)**:
- Key observations organized by theme
- Phase 2 design discussion

**Technical Appendix (Slides 30-47)**:
- Model structure and assumptions
- Data sources and parameters

This structure itself represents sophisticated "use scaffolding" - showing how to communicate multidimensional scenario analysis effectively.

