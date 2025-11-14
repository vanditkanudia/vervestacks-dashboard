# VerveStacks Python Service

This service provides a FastAPI interface to VerveStacks energy modeling data for the dashboard.

## 🏗️ Architecture

The service follows the **Service Layer Pattern** with **Dependency Injection**:

- **API Layer**: FastAPI endpoints handle HTTP requests/responses
- **Service Layer**: `VerveStacksService` contains business logic and data processing
- **Repository Layer**: VerveStacks functions handle data access

## 🚀 Getting Started

### Installation

```bash
cd python-service
pip install -r requirements.txt
```

### Running the Service

```bash
python api_server.py
```

The service will run on `http://localhost:5000`

## 📊 Available Endpoints

### Health Check
- `GET /health` - Service status and module availability

### Generation Profile
- `POST /generate-profile` - Generate demand-shaped generation profiles
- `GET /capacity-by-fuel/{iso_code}/{year}` - Get capacity by fuel type

### Dashboard Overview Data (NEW)
- `GET /overview/energy-analysis/{iso_code}` - Comprehensive energy analysis
- `GET /overview/capacity-utilization/{iso_code}` - Capacity utilization data
- `GET /overview/technology-mix/{iso_code}` - Technology mix and capacity
- `GET /overview/co2-intensity/{iso_code}` - CO2 intensity and fuel consumption

## 🔧 Service Layer Methods

### VerveStacksService

- `get_energy_analysis(iso_code, year)` - Complete energy analysis
- `get_capacity_utilization(iso_code, year)` - Utilization factors from IRENA/EMBER
- `get_technology_mix(iso_code, year)` - Technology breakdown and capacity
- `get_co2_intensity(iso_code, year)` - CO2 metrics and fuel consumption

## 📁 Project Structure

```
python-service/
├── api_server.py              # FastAPI application
├── services/
│   ├── __init__.py           # Package initialization
│   └── vervestacks_service.py # VerveStacks business logic
├── requirements.txt           # Python dependencies
└── README.md                 # This file
```

## 🔄 Data Flow

1. **API Request** → FastAPI endpoint
2. **Dependency Injection** → Service layer
3. **Business Logic** → VerveStacks processing
4. **Data Processing** → Existing VerveStacks functions
5. **Response** → Formatted data for dashboard charts

## 🎯 Data Sources

- **GEM**: Global Energy Monitor plant-level data
- **IRENA**: International Renewable Energy Agency statistics
- **EMBER**: Global electricity review data
- **UNSD**: United Nations energy statistics

## 🚨 Error Handling

All endpoints include comprehensive error handling:
- Service availability checks
- Data processing error handling
- User-friendly error messages
- Proper HTTP status codes

## 🔍 Testing

Test the service health:
```bash
curl http://localhost:5000/health
```

Test overview endpoints:
```bash
curl http://localhost:5000/overview/energy-analysis/JPN
curl http://localhost:5000/overview/capacity-utilization/USA
curl http://localhost:5000/overview/technology-mix/DEU
curl http://localhost:5000/overview/co2-intensity/CHN
```
