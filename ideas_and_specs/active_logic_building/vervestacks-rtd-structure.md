# VerveStacks Documentation Structure

## 🏠 **Home / Landing Page**
```
index.rst
├── Hero: "Energy Modeling That Starts Where Others Stop"
├── The open USE vision
├── The precise offering - what is free and what are its usecases
```

## 📚 **Main Documentation Sections**

### **1. Getting Started** (`/getting-started/`)
```
getting-started/
├── index.rst                 # the resources - github repo, data dump, Veda-TIMES model; Veda online
├── quickstart.rst            # 5-minute first model run
├── first-scenario.rst        # Build your first scenario
├── understanding-outputs.rst # Reading results
└── faq.rst                   # Common questions
```

### **2. Using VerveStacks** (`/usage/`)
```
usage/
├── index.rst
├── web-interface/
│   ├── veda-online.rst      # Using Veda Online
│   └── results-viewer.rst
├── local-usage/
│   ├── installation.rst
│   └── running-models.rst
├── scenarios/
│   ├── creating-scenarios.rst
│   ├── policy-constraints.rst
│   ├── technology-options.rst
│   └── demand-projections.rst
└── outputs/
    ├── understanding-results.rst
    ├── visualization.rst
    └── export-formats.rst
```

### **3. Model Architecture** (`/architecture/`)
```
architecture/
├── index.rst
├── times-framework/
│   ├── overview.rst
│   ├── timeslices.rst
│   ├── commodities.rst
│   └── processes.rst
├── data-structure/
│   ├── plant-database.rst
│   ├── demand-profiles.rst
│   ├── resource-potentials.rst
│   └── cost-assumptions.rst
├── model-features/
│   ├── retrofit-logic.rst
│   ├── ev-integration.rst
│   ├── storage-modeling.rst
│   ├── ccs-pathways.rst
│   └── transmission.rst
└── calibration/
    ├── historical-validation.rst
    └── benchmarking.rst
```

### **4. Developer Guide** (`/developers/`)
```
developers/
├── index.rst
├── contributing.rst
├── data-pipeline/
│   ├── overview.rst
│   ├── data-sources.rst
│   ├── processing-scripts.rst
│   └── quality-checks.rst
├── model-building/
│   ├── template-structure.rst
│   ├── adding-regions.rst
│   ├── technology-definitions.rst
│   └── debugging.rst
├── api-reference/
│   ├── python-api.rst
│   ├── data-formats.rst
│   └── solver-interfaces.rst
└── extensions/
    ├── custom-modules.rst
    ├── emulator-development.rst
    └── plugin-system.rst
```

### **5. Use Cases** (`/use-cases/`)
```
use-cases/
├── index.rst
├── policy-analysis/
│   ├── carbon-pricing.rst
│   ├── renewable-targets.rst
│   └── grid-reliability.rst
├── investment-planning/
│   ├── generation-expansion.rst
│   ├── transmission-needs.rst
│   └── storage-deployment.rst
├── research-applications/
│   ├── academic-studies.rst
│   ├── comparative-analysis.rst
│   └── sensitivity-testing.rst
└── case-studies/
    ├── texas-transition.rst
    ├── european-green-deal.rst
    └── emerging-markets.rst
```

### **6. Theory & Methods** (`/theory/`)
```
theory/
├── index.rst
├── optimization-basics.rst
├── temporal-resolution/
│   ├── timeslice-design.rst
│   ├── chronological-dispatch.rst
│   └── storage-coupling.rst
├── capacity-planning/
│   ├── screening-curves.rst
│   ├── reliability-metrics.rst
│   └── capacity-credit.rst
├── economic-framework/
│   ├── objective-function.rst
│   ├── discount-rates.rst
│   └── cost-recovery.rst
└── assumptions/
    ├── technology-costs.rst
    ├── fuel-prices.rst
    └── demand-forecasts.rst
```

### **7. Tutorials** (`/tutorials/`)
```
tutorials/
├── index.rst
├── beginner/
│   ├── 01-your-first-model.rst
│   ├── 02-changing-carbon-price.rst
│   ├── 03-adding-renewable-target.rst
│   └── 04-comparing-scenarios.rst
├── intermediate/
│   ├── 01-custom-constraints.rst
│   ├── 02-demand-response.rst
│   ├── 03-sector-coupling.rst
│   └── 04-stochastic-analysis.rst
├── advanced/
│   ├── 01-model-linking.rst
│   ├── 02-decomposition.rst
│   ├── 03-monte-carlo.rst
│   └── 04-custom-solvers.rst
└── video-tutorials/
    └── index.rst  # Embedded videos
```

### **8. Community** (`/community/`)
```
community/
├── index.rst
├── contributing.rst
├── code-of-conduct.rst
├── support.rst
├── consultants.rst      # Partner network
├── publications.rst     # Papers using VS
└── roadmap.rst
```

### **9. Reference** (`/reference/`)
```
reference/
├── index.rst
├── glossary.rst
├── parameters/
│   ├── demand.rst
│   ├── technologies.rst
│   ├── commodities.rst
│   └── constraints.rst
├── data-sources.rst
├── citations.rst
├── changelog.rst
└── license.rst
```

## 📝 **Key Documentation Principles**

### **Progressive Disclosure**
- Start with "what" and "why" before "how"
- Layer complexity - don't overwhelm newcomers
- Provide clear learning paths

### **Multiple Entry Points**
- **For Policymakers**: Use cases, case studies, web interface
- **For Researchers**: Theory, methods, API reference
- **For Consultants**: Customization, extensions, business model
- **For Students**: Tutorials, theory, getting started

### **Documentation Types**
1. **Explanatory** - Conceptual understanding
2. **How-to Guides** - Task completion
3. **Reference** - Technical specifications
4. **Tutorials** - Learning journeys

### **Special Features**

#### **Interactive Elements**
```python
# Embedded Jupyter notebooks for tutorials
# Live model parameter editors
# Result visualization widgets
```

#### **Search Optimization**
- Comprehensive glossary with energy sector terms
- Common search redirects (e.g., "LCOE" → "Levelized Cost")
- Tagged content for role-based filtering

#### **Version Management**
```
/stable/     # Current stable release
/latest/     # Development version
/v1.0/       # Historical versions
```

## 🎨 **Styling & Branding**

### **Custom Theme Elements**
```css
/* Clean, modern design */
- Sans-serif typography
- High contrast for readability
- VS brand colors (suggest: deep blue + vibrant accent)
- Interactive diagrams using D3.js
- Responsive design for mobile access
```

### **Navigation Helpers**
- Breadcrumbs on all pages
- "Next steps" boxes at section ends
- Role-based quick links in sidebar
- Estimated reading time for longer pages

## 🚀 **Launch Priorities**

### **Phase 1: Core Documentation**
1. Getting Started
2. Model Library (2-3 example models)
3. Basic Usage guides
4. FAQ

### **Phase 2: Technical Depth**
1. Architecture documentation
2. Developer guides
3. API reference
4. First tutorials

### **Phase 3: Community Building**
1. Use cases
2. Case studies
3. Community section
4. Advanced tutorials

## 📊 **Metrics & Feedback**
- Analytics on most-visited pages
- Feedback widget on each page
- Regular documentation surveys
- Community contribution tracking