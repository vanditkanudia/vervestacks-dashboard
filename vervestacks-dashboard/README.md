# VerveStacks Dashboard

A professional web interface that makes VerveStacks energy modeling accessible to users worldwide. Transform energy modeling from an elite technical craft to an accessible analytical tool.

## 🚨 **FOR NEW DEVELOPERS/AI AGENTS - READ THIS FIRST**

**Before making any changes to this project, you MUST read these documents in order:**

1. **[`DEVELOPMENT_RULES.md`](./DEVELOPMENT_RULES.md)** - **🚨 CRITICAL: All development rules and context**
2. **[`DASHBOARD_ARCHITECTURE.md`](./DASHBOARD_ARCHITECTURE.md)** - How and why the system was built
3. **[`FEATURES_DEVELOPMENT.md`](./FEATURES_DEVELOPMENT.md)** - What you're building and when

**This project has specific rules and philosophy that MUST be followed. Reading these documents will save you time and prevent mistakes.**

---

## 🎯 **What is VerveStacks Dashboard?**

## 🚀 **Quick Start**

```bash
# Install dependencies
cd frontend && npm install
cd ../backend && npm install
cd ../python-service && pip install -r requirements.txt

# Start services (in separate terminals)
cd backend && npm start
cd python-service && python api_server.py
cd frontend && npm start
```

## ✨ **Features**

### ✅ **Completed**
- **Interactive World Map**: Navigate countries with visual indicators
- **Country Dashboard**: Tabbed interface for comprehensive analysis
- **Hourly Electricity Generation Profile Generator**: Python integration with EMBER data
- **Modern Design System**: Beautiful purple gradients and professional UI

### 🔄 **In Development**
- Time Series Analysis
- Grid Network Visualization
- Operational Analysis
- Reports & Export

## 🏗️ **Architecture**

- **Frontend**: React + TypeScript + Tailwind CSS
- **Backend**: Node.js + Express.js
- **Python Service**: FastAPI for energy modeling functions
- **Data**: Integration with VerveStacks Python scripts

## 🎨 **Design System**

Our dashboard uses a centralized design system with beautiful purple gradients and professional styling. See [`DESIGN_SYSTEM.md`](./frontend/DESIGN_SYSTEM.md) for complete details.

## 📚 **Documentation**

This project is thoroughly documented to help developers, users, and stakeholders understand the system:

- **[`DEVELOPMENT_RULES.md`](./DEVELOPMENT_RULES.md)** - **🚨 CRITICAL: Development rules, context, and philosophy (READ FIRST)**
- **[`DASHBOARD_ARCHITECTURE.md`](./DASHBOARD_ARCHITECTURE.md)** - How and why the dashboard was built (for developers)
- **[`FEATURES_DEVELOPMENT.md`](./FEATURES_DEVELOPMENT.md)** - What users can do and when features will be built
- **[`frontend/DESIGN_SYSTEM.md`](./frontend/DESIGN_SYSTEM.md)** - Visual design rules and component library
- **[`POTENTIAL_DASHBOARD_FEATURES.md`](./POTENTIAL_DASHBOARD_FEATURES.md)** - Future feature ideas and possibilities

## 🔧 **Development**

See [`DASHBOARD_ARCHITECTURE.md`](./DASHBOARD_ARCHITECTURE.md) for detailed development guidelines and architecture decisions.
