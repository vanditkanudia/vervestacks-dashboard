# VerveStacks Dashboard - Development Rules & Context

## 📋 **PURPOSE OF THIS DOCUMENT**

**This document contains ALL the specific rules, context, and philosophy established during development. If you're a new developer or AI agent, READ THIS FIRST before making any changes.**

**This is your "developer handbook" - it contains everything you need to know to work on this project correctly.**

---

## 🚨 **CRITICAL DEVELOPMENT RULES - NEVER VIOLATE THESE**

### **Rule 1: NO FALLBACK FUNCTIONS**
- **🚫 NEVER**: Create mock data, dummy functions, or fallback implementations
- **✅ ALWAYS**: Integrate with real Python services and actual data
- **Why**: This is a REAL energy modeling tool, not a demo. Users need actual results.

### **Rule 2: COMPREHENSIVE ERROR HANDLING**
- **🚫 NEVER**: Let errors crash the app or show technical jargon
- **✅ ALWAYS**: Handle errors gracefully with user-friendly messages
- **Why**: Users need to understand what went wrong, not see technical errors.

### **Rule 3: CONSISTENT UNITS**
- **🚫 NEVER**: Mix units or use incorrect energy industry standards
- **✅ ALWAYS**: Use GW for capacity, TWh for production/demand
- **Why**: Energy industry standard units that users expect and understand.

### **Rule 4: DESIGN SYSTEM COMPLIANCE**
- **🚫 NEVER**: Write custom CSS or create new styling patterns
- **✅ ALWAYS**: Use design system classes (.btn-primary, .card, .input-field, etc.)
- **Why**: Consistency across the entire application and easy maintenance.

### **Rule 5: DATABASE INTEGRATION**
- **🚫 NEVER**: Use mock database calls or ignore database errors
- **✅ ALWAYS**: Use the PostgreSQL connection pool and handle database operations properly
- **Why**: Real data persistence is critical for user analysis and results.

### **Rule 6: PYTHON SERVICE INTEGRATION**
- **🚫 NEVER**: Create fallback data or ignore Python service availability
- **✅ ALWAYS**: Check Python service health and provide clear error messages
- **Why**: The core energy modeling functionality depends on Python services.

---

## 🎯 **PROJECT PHILOSOPHY - UNDERSTAND THIS FIRST**

### **Mission Statement**
Transform energy modeling from an **elite technical craft to an accessible analytical tool** - moving beyond Open SOURCE to Open USABILITY.

### **Core Design Principle: Option A - Pure Tabbed Interface**
We chose **Option A** (tabbed interface) over alternatives because:
- **Context Preservation**: Users stay in the same dashboard when switching analysis types
- **Professional Appearance**: Looks like enterprise software (Tableau, Power BI)
- **Scalable**: Easy to add new analysis types without restructuring navigation
- **Intuitive**: Users understand tabs from other applications

### **User Experience Philosophy**
1. **Progressive Disclosure**: Information revealed through logical tab progression
2. **No Page Jumping**: Users stay in context throughout their analysis
3. **Consistent Interaction**: Same patterns across all analysis types
4. **Professional Polish**: Beautiful design that reflects analysis quality

---

## 🏗️ **ARCHITECTURE DECISIONS - WHY WE BUILT IT THIS WAY**

### **Three-Tier Architecture**
```
React Frontend → Node.js Backend → Python FastAPI → VerveStacks Scripts
```

**Why This Architecture?**
- **Separation of Concerns**: Each layer has a specific responsibility
- **Technology Specialization**: React for UI, Node.js for API, Python for analysis
- **Scalability**: Can scale each layer independently
- **Maintainability**: Clear boundaries make debugging easier

### **Database Integration**
- **PostgreSQL**: Robust, scalable relational database
- **Connection Pooling**: Efficient database connection management
- **Schema Management**: Dedicated `vervestacks` schema for organization
- **Data Persistence**: Real user data and analysis results

---

## 🔧 **COMPONENT DEVELOPMENT RULES**

### **Tab Pattern - ALWAYS FOLLOW THIS STRUCTURE**
```javascript
const AnalysisTab = () => {
  return (
    <div className="tab-content">
      <div className="tab-header">
        <h2>Analysis Title</h2>
        <p>Description of what this analysis does</p>
      </div>
      
      <div className="tab-controls">
        {/* Input parameters and action buttons */}
      </div>
      
      <div className="tab-visualization">
        {/* Charts, graphs, or data displays */}
      </div>
      
      <div className="tab-summary">
        {/* Key insights and statistics */}
      </div>
    </div>
  );
};
```

**Why This Pattern?**
- **Consistency**: All tabs look and behave the same way
- **User Experience**: Users know what to expect in each tab
- **Maintainability**: Easy to update and modify
- **Scalability**: New tabs follow the same structure

### **State Management Pattern - ALWAYS USE THIS**
```javascript
const [loading, setLoading] = useState(false);
const [error, setError] = useState(null);
const [data, setData] = useState(null);

const handleAnalysis = async () => {
  setLoading(true);
  setError(null);
  
  try {
    const result = await api.analyze(params);
    setData(result);
  } catch (err) {
    setError(err.message);
  } finally {
    setLoading(false);
  }
};
```

**Why This Pattern?**
- **User Feedback**: Users always know what's happening
- **Error Handling**: Errors are captured and displayed properly
- **Loading States**: UI shows progress and prevents multiple submissions
- **Consistency**: Same pattern across all components

---

## 🎨 **DESIGN SYSTEM RULES - NEVER DEVIATE FROM THESE**

### **Button Classes - ALWAYS USE THESE**
```javascript
// ✅ CORRECT - Use design system
<button className="btn-primary">Generate Analysis</button>
<button className="btn-outline">Cancel</button>
<button className="btn-success">Save</button>

// ❌ WRONG - Custom styling
<button className="custom-button">Generate Analysis</button>
<button style={{ backgroundColor: 'blue' }}>Cancel</button>
```

### **Card Classes - ALWAYS USE THESE**
```javascript
// ✅ CORRECT - Use design system
<div className="card">Content</div>
<div className="card-elevated">Important Content</div>

// ❌ WRONG - Custom styling
<div className="custom-card">Content</div>
<div style={{ boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}>Content</div>
```

### **Input Classes - ALWAYS USE THESE**
```javascript
// ✅ CORRECT - Use design system
<input className="input-field" />
<input className="input-field-success" />
<input className="input-field-error" />

// ❌ WRONG - Custom styling
<input className="custom-input" />
<input style={{ border: '1px solid #ccc' }} />
```

### **Why These Rules?**
- **Consistency**: All components look the same
- **Maintainability**: Change colors/buttons in one place
- **Professional Appearance**: Unified look across the application
- **Developer Experience**: Clear rules for building components

---

## 🔄 **INTEGRATION PATTERNS - ALWAYS USE THESE**

### **Python Service Integration**
```javascript
// ✅ CORRECT - Use the Python executor
import { pythonExecutor } from '../utils/pythonExecutor';

const result = await pythonExecutor.executeGenerationProfile(
  isoCode, 
  year, 
  totalGenerationTwh
);

// ❌ WRONG - Direct API calls or mock data
const result = await fetch('/api/generate-profile', {...});
// or
const result = mockGenerationData;
```

### **Database Integration**
```javascript
// ✅ CORRECT - Use database connection pool
import { db } from '../database/connection';

const result = await db.query('SELECT * FROM countries WHERE iso_code = $1', [isoCode]);

// ❌ WRONG - Mock database calls
const result = mockCountriesData;
```

### **Error Handling Pattern**
```javascript
try {
  const result = await pythonExecutor.executeAnalysis(params);
  return result;
} catch (error) {
  if (error.code === 'ECONNREFUSED') {
    throw new Error('Python service not running. Start it with: cd python-service && python api_server.py');
  }
  throw new Error(`Analysis failed: ${error.message}`);
}
```

**Why This Pattern?**
- **User-Friendly**: Users understand what went wrong
- **Actionable**: Users know how to fix the problem
- **Professional**: No technical jargon or crash messages
- **Consistent**: Same error handling across all components

---

## 📱 **RESPONSIVE DESIGN RULES**

### **Breakpoint Strategy - ALWAYS FOLLOW THESE**
- **Large**: 1024px+ (Full dashboard experience)
- **Medium**: 768px-1023px (Tabbed interface optimized)
- **Small**: <768px (Mobile-optimized layout)

### **Mobile-First Approach**
- **Start with mobile**: Design for small screens first
- **Progressive enhancement**: Add features for larger screens
- **Touch-friendly**: All interactions must work on touch devices
- **Simplified navigation**: Mobile users get streamlined experience

---

## 🚀 **PERFORMANCE RULES**

### **Lazy Loading - ALWAYS IMPLEMENT**
- **Tabs**: Load content only when tab is selected
- **Charts**: Render charts only when visible
- **Data**: Fetch data only when needed
- **Images**: Lazy load images and heavy assets

### **Caching Strategy - ALWAYS IMPLEMENT**
- **API Responses**: Cache repeated requests
- **Chart Configurations**: Reuse chart options
- **User Preferences**: Remember user settings
- **Static Assets**: Cache CSS, JS, and images

---

## 🔐 **SECURITY RULES**

### **Authentication - ALWAYS IMPLEMENT**
- **JWT Tokens**: Secure, stateless authentication
- **Role-Based Access**: Different permission levels
- **Session Management**: Secure session handling
- **API Protection**: Rate limiting and validation

### **Input Validation - ALWAYS IMPLEMENT**
- **User Inputs**: Validate all user inputs
- **API Parameters**: Validate all API parameters
- **File Uploads**: Validate file types and sizes
- **SQL Injection**: Use parameterized queries

---

## 📊 **TESTING RULES**

### **Before Deploying - ALWAYS TEST THESE**
- **User Flows**: Complete user journeys work end-to-end
- **Error Scenarios**: Error handling works correctly
- **Responsive Design**: Works on all device sizes
- **Performance**: Meets performance targets
- **Accessibility**: Keyboard navigation and screen readers work

---

## 🎯 **QUICK REFERENCE - MOST IMPORTANT RULES**

### **🚫 NEVER DO THESE:**
1. Create fallback/mock functions
2. Use custom CSS instead of design system
3. Skip error handling
4. Use wrong units (GW for capacity, TWh for production)
5. Break the tab pattern structure
6. Ignore responsive design
7. Skip input validation
8. Ignore database integration
9. Create mock Python service responses

### **✅ ALWAYS DO THESE:**
1. Follow the tab pattern structure
2. Use design system classes
3. Integrate with real Python services
4. Handle errors gracefully
5. Use correct energy units
6. Test on all device sizes
7. Validate all user inputs
8. Use database connection pool
9. Check Python service health

---

## 📚 **RELATED DOCUMENTATION**

- **Architecture & Philosophy**: [`DASHBOARD_ARCHITECTURE.md`](./DASHBOARD_ARCHITECTURE.md) - HOW & WHY (for developers)
- **Features Development**: [`FEATURES_DEVELOPMENT.md`](./FEATURES_DEVELOPMENT.md) - WHAT & WHEN (for users & project management)
- **Design System**: [`frontend/DESIGN_SYSTEM.md`](./frontend/DESIGN_SYSTEM.md) - Visual design rules and components

---

## 🎯 **FOR NEW DEVELOPERS/AI AGENTS**

### **Before You Start Coding:**
1. **Read this document** to understand all the rules
2. **Read Architecture.md** to understand the technical foundation
3. **Read Features.md** to understand what you're building
4. **Follow ALL the rules** above - no exceptions

### **Remember:**
- **This is a REAL tool**, not a demo
- **User experience is prioritized** over technical complexity
- **Consistency is key** - follow established patterns
- **When in doubt**, refer to this document

---

*This document contains ALL the rules and context established during development. Follow these rules to maintain consistency, quality, and user experience across the VerveStacks Dashboard.*
