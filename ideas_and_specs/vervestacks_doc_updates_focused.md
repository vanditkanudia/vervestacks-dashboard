# VerveStacks Documentation Updates - Focused Revisions

## **1. MAIN INTRODUCTION (`index.rst`) - Strategic Additions**

### **Replace the current "Open-Use Vision" section with:**

```rst
The Excavator Approach
----------------------

Most modeling projects begin by building the model. VerveStacks begins where others stop — with **ready‑to‑use, decision‑grade power‑sector models** you can explore immediately.

**The Industry Debate:**
   "TIMES-VEDA is proprietary! Use free, open-source tools like OSeMOSYS instead!"

**The Real Problem:**
   Whether you used premium tools or free tools, **you were still spending months building models**.

**The VerveStacks Insight:**
   The issue wasn't tool cost — it was **that people were building at all**.

While the industry focused on making shovels free, **we made digging obsolete**.

Open‑Use Vision
---------------

- **Skip the building phase.** Don't spend months creating infrastructure just to test a question. Start with solved, credible models and focus on **scenarios and insights**.
- **Democratize model usage, not model building.** The bottleneck isn't access to modeling tools — it's the time required to create useful models. VerveStacks eliminates that bottleneck entirely.
- **Focus on what matters.** Domain experts shouldn't become pipeline engineers. They should ask better questions, run scenarios fast, and interpret results with confidence — **all without building anything**.
- **Managed complexity.** Free tools can expose complexity raw; proprietary tools can hide it entirely. VerveStacks makes complexity *usable* — transparent data, explicit methods, practical defaults, and instant deployment.
```

### **Update "By the Numbers" to emphasize speed:**

```rst
By the Numbers
--------------

- **5 minutes**: From country selection to running scenarios (vs. months of building)
- **100+ countries**: Ready-to-use models available immediately  
- **8760 hours**: Native hourly resolution with intelligent aggregation
- **50×50km**: Spatial resolution for renewable resource modeling
- **6+ datasets**: Integrated global energy data (IRENA, EMBER, GEM, REZoning, Atlite, AR6)
- **Zero setup**: Complete modeling value chain with no installation or configuration
```

---

## **2. OPEN-USE MOVEMENT (`community/open-use-movement.rst`) - Major Revision**

### **Replace the entire "What's broken in the current 'open' story" section:**

```rst
What's broken in the "free shovels" story
==========================================

The energy modeling community got trapped in the wrong debate.

**The Debate:** "Proprietary vs. Free Tools"
   - Critics: "TIMES-VEDA is a proprietary black box! Use free, transparent alternatives!"
   - Response: "Here are free, open-source modeling frameworks for everyone!"

**The Reality:** Whether you used expensive shovels or free shovels, **you were still digging holes for months**.

**The Missing Ambition:** Instead of making tools more accessible, why not **make the tools unnecessary**?

Free Shovels Approach
~~~~~~~~~~~~~~~~~~~~~~

**What the industry did:**
   - Created free alternatives to proprietary modeling tools
   - Simplified frameworks to reduce learning curves
   - Open-sourced code for transparency
   - Trained more people to use the free tools

**The result:**
   - ✓ Removed licensing barriers
   - ✓ Increased transparency  
   - ✓ Simplified some workflows
   - ✗ **Still takes months to build useful models**

Excavator Approach
~~~~~~~~~~~~~~~~~~

**What VerveStacks does:**
   - Automates model creation entirely
   - Provides instant access to institutional-grade models
   - Focuses user time on analysis, not building
   - Eliminates the expertise barrier to model usage

**The result:**
   - ✓ Minutes to deployment, not months
   - ✓ Anyone can analyze energy systems immediately
   - ✓ Higher quality than manual processes
   - ✓ **Complete transparency with parameter traceability**

.. epigraph::

   **"While others argued about shovel pricing, we made digging obsolete."**

The Ambition Gap
~~~~~~~~~~~~~~~~

**Free Shovels Thinking:** "How do we make modeling tools more accessible?"
**VerveStacks Thinking:** "How do we make modeling tools unnecessary?"

**Free Shovels Goal:** More people building models
**VerveStacks Goal:** Nobody building models

**Free Shovels Success:** Reduced barriers to model creation  
**VerveStacks Success:** Eliminated need for model creation

This isn't about incremental improvement — it's about **strategic ambition** to solve the real problem.
```

### **Update the "What 'Open Use' means" section:**

```rst
What "Open Use" means
=====================

**Open Use** is the commitment to publish **decision-grade, pre-solved, shareable models** that anyone can open, explore, and extend **today** — without spending months building anything.

**Open Use** doesn't replace open source. It **transcends** it by focusing on **model usage** rather than **model building**.

**Traditional "Open" Approach:**
   - Open source code → ✓ Transparency
   - Free licensing → ✓ Accessibility  
   - Community development → ✓ Collaboration
   - **Months to build models** → ✗ Time barrier remains

**Open Use Approach:**
   - Open model access → ✓ Immediate usage
   - Complete parameter traceability → ✓ Superior transparency
   - Instant deployment → ✓ Zero time barrier  
   - **Focus on insights, not infrastructure** → ✓ Real democratization

With **VerveStacks** this looks like:

* **Freely available, ISO-level country models** (100+ target countries) — **ready to use immediately**.

* **Complete transparency**: Every parameter traceable to source data and transformation logic.

* **Pre-solved online** in **Veda Online** — no install, no solver management, no months of setup.

* **Assumption layers ("stacks")** you can toggle: WEO / NREL / NGFS, AR6 R10 climate categories.

* **Stress-based timeslices**: Intelligent temporal aggregation that preserves physics while maintaining solvability.

* **"Microscope mode"**: Import any capacity mix and get operational diagnostics instantly.

**Open Use** measures success in **time-to-insight**, not just code availability.
```

### **Update "Positioning vs frameworks" section:**

```rst
Positioning vs frameworks
=========================

**The Old Debate:** "Which modeling framework should I use?"

**The VerveStacks Answer:** "Why are you building models at all?"

Framework Comparison
~~~~~~~~~~~~~~~~~~~~

* **Traditional TIMES**: Sophisticated but requires months of model building
* **OSeMOSYS / Temoa**: Simpler and free but still requires months of model building  
* **VerveStacks**: Built on proven TIMES foundation with **5-minute deployment**

**All frameworks can produce good models.** The question is: **How long does it take to get there?**

Interoperability Strategy
~~~~~~~~~~~~~~~~~~~~~~~~~

VerveStacks provides **model-agnostic data artifacts** and can export to multiple frameworks:

* **TIMES users**: Get fully functional Veda bundles immediately
* **OSeMOSYS users**: Use VerveStacks as the **starting point** or **validation benchmark**  
* **PyPSA users**: Import VerveStacks data for power system analysis
* **Any framework**: Use VerveStacks as the **microscope** for external capacity plans

**The goal isn't framework lock-in** — it's **eliminating the building phase** regardless of your preferred optimization engine.
```

### **Update the FAQ section:**

```rst
FAQ
===

**Isn't this just another proprietary system?**
VerveStacks provides **complete parameter traceability** — every value traceable to source data and transformation logic. This is **more transparent** than most open-source alternatives, which show you the code but not the data lineage.

**Why not just use free tools like OSeMOSYS?**
Free tools are great — if you have months to build models. VerveStacks is for when you want to **analyze energy systems today**, not build infrastructure for months first.

**What about the "open source" principle?**
We're **open use** rather than just open source. The goal is **democratizing model usage**, not just democratizing model building. Anyone can access institutional-grade models instantly — that's more democratic than requiring months of technical expertise.

**How is this different from existing model libraries?**
Most model libraries provide **model files** that still require setup, validation, and customization. VerveStacks provides **solved, interactive models** you can explore immediately in your browser.

**What if I want to modify the underlying assumptions?**
Every assumption is documented and traceable. You can fork the inputs, modify what you need, and VerveStacks will regenerate a clean model. **No need to rebuild from scratch.**
```

---

## **Key Changes Summary:**

### **Strategic Shifts:**
1. **From**: "Open source vs. proprietary" → **To**: "Building vs. using"
2. **From**: "Tool accessibility" → **To**: "Model accessibility"  
3. **From**: "Free tools" → **To**: "Free time"
4. **From**: "Democratizing building" → **To**: "Democratizing usage"

### **Messaging Focus:**
- **Lead with the time savings** (5 minutes vs. months)
- **Emphasize the strategic ambition** (excavator vs. shovels)
- **Show superior transparency** (parameter traceability vs. code access)
- **Highlight real democratization** (anyone can analyze vs. anyone can build)

### **Tone:**
- **Confident but not arrogant** - acknowledging that others could have done this, just didn't have the ambition
- **Problem-focused** - addressing the real bottleneck, not the perceived one
- **User-centric** - emphasizing what users actually want (insights, not infrastructure)

This framing positions VerveStacks as **strategically ambitious** rather than just technically superior, which is much more compelling and accurate!
