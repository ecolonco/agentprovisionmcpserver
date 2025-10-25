# 🧠 MCP Server (Mapping & Control Plane)

**The AI orchestration and integration backbone for DataFlow AI**

MCP Server is the control plane and data sync manager for all business integrations, powering AgentProvision - the customizable ERP for roll-ups like Silvercreek Dental Partners.

---

## 🌟 Overview

The MCP Server normalizes, maps, and orchestrates data flows from multiple enterprise systems into a single unified API and data warehouse layer called **DentalERP**.

### Supported Integrations

- **ADP** → Payroll data
- **Eaglesoft** → Procedures, payments, visits
- **DentalIntel** → Production KPIs
- **NetSuite** → Financial GL, AP/AR
- **Merchant Processors** → Payments, deposits

---

## 🏗️ Architecture

### Technology Stack

| Component | Technology |
|-----------|-----------|
| **Framework** | FastAPI (Python 3.11) |
| **Database** | PostgreSQL 15 with SQLAlchemy |
| **Caching** | Redis 7 |
| **Queue** | Kafka (or Redis Streams) |
| **Orchestration** | Temporal.io (preferred) / Airflow |
| **Data Transforms** | dbt models |
| **Observability** | Prometheus + Grafana + OpenTelemetry |
| **Authentication** | JWT + API Keys |
| **Containerization** | Docker + Docker Compose |
| **IaC** | Terraform |

### Core Features

✅ **Stateless Microservice** with scalable REST + gRPC endpoints
✅ **Modular Connectors** for each integration system
✅ **Mapping Registry** for cross-system entity resolution
✅ **Workflow Orchestration** for data ingestion, validation, transformation, and sync
✅ **Event-Driven Architecture** via Kafka topics
✅ **Complete Observability** with metrics, logs, and traces

---

## 📁 Project Structure

```
/mcp-server
├── src/
│   ├── api/
│   │   ├── main.py                 # FastAPI entrypoint
│   │   └── routers/
│   │       ├── health.py           # Health check endpoints
│   │       ├── mappings.py         # Mapping registry endpoints
│   │       └── sync.py             # Sync and workflow endpoints
│   ├── core/
│   │   ├── config.py               # Configuration management
│   │   └── security.py             # Authentication & authorization
│   ├── db/
│   │   ├── models.py               # SQLAlchemy models
│   │   ├── schemas.py              # Pydantic schemas
│   │   ├── crud.py                 # CRUD operations
│   │   └── database.py             # Database connection
│   ├── integrations/
│   │   ├── adp_connector.py        # ADP integration
│   │   ├── eaglesoft_connector.py  # Eaglesoft integration
│   │   ├── dentalintel_connector.py
│   │   ├── netsuite_connector.py
│   │   └── bank_connector.py
│   ├── orchestration/
│   │   ├── workflows.py            # Temporal workflows
│   │   └── tasks.py                # Task definitions
│   └── utils/
│       ├── logger.py               # Logging configuration
│       └── telemetry.py            # OpenTelemetry setup
│
├── scripts/
│   ├── seed_db.py                  # Database seeding
│   └── init_db.sql                 # SQL initialization
│
├── monitoring/
│   ├── prometheus.yml              # Prometheus config
│   └── grafana-datasources.yml     # Grafana config
│
├── terraform/                       # Infrastructure as Code
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
│
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)
- PostgreSQL 15+
- Redis 7+

### 1. Clone and Setup

```bash
git clone <repository-url>
cd AgentprovisionMCPserver

# Copy environment file
cp .env.example .env

# Edit .env with your configuration
nano .env
```

### 2. Start with Docker Compose

```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f mcp-server

# Check health
curl http://localhost:8000/api/v1/health
```

### 3. Access Services

| Service | URL | Credentials |
|---------|-----|-------------|
| **API Docs** | http://localhost:8000/docs | - |
| **API** | http://localhost:8000/api/v1 | API Key or JWT |
| **Prometheus** | http://localhost:9091 | - |
| **Grafana** | http://localhost:3000 | admin / admin |
| **PostgreSQL** | localhost:5432 | mcpuser / mcppassword |
| **Redis** | localhost:6379 | - |

---

## 🔧 Development

### Local Setup (without Docker)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql+asyncpg://mcpuser:mcppassword@localhost:5432/mcpdb"
export REDIS_URL="redis://localhost:6379/0"

# Run database migrations (if using Alembic)
alembic upgrade head

# Seed database
python -m scripts.seed_db

# Run server
python src/api/main.py
# Or with uvicorn
uvicorn src.api.main:app --reload
```

### Database Management

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1

# Seed sample data
python -m scripts.seed_db
```

---

## 📡 API Usage

### Authentication

The API supports two authentication methods:

#### 1. API Key (Recommended for integrations)

```bash
curl -X GET "http://localhost:8000/api/v1/mappings" \
  -H "X-API-Key: your-api-key"
```

#### 2. JWT Bearer Token

```bash
curl -X GET "http://localhost:8000/api/v1/mappings" \
  -H "Authorization: Bearer your-jwt-token"
```

### Example Endpoints

#### Register a Mapping

```bash
curl -X POST "http://localhost:8000/api/v1/mappings/register" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "source_system": "adp",
    "source_id": "EMP-12345",
    "source_entity_type": "employee",
    "target_system": "dentalerp",
    "target_id": "ERP-EMP-001",
    "target_entity_type": "employee",
    "confidence_score": 100
  }'
```

#### Trigger a Sync Workflow

```bash
curl -X POST "http://localhost:8000/api/v1/workflows/run" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_type": "sync_employees",
    "source_system": "adp",
    "target_system": "dentalerp",
    "entity_type": "employee",
    "config": {
      "batch_size": 100,
      "full_sync": true
    }
  }'
```

#### Check Sync Status

```bash
curl -X GET "http://localhost:8000/api/v1/sync/status?source_system=adp&target_system=dentalerp&entity_type=employee" \
  -H "X-API-Key: your-api-key"
```

---

## 🔌 Adding New Integrations

### 1. Create Connector Module

Create `src/integrations/your_system_connector.py`:

```python
"""
Your System Integration Connector
"""
import httpx
from typing import List, Dict, Any
from src.core.config import get_integration_config
from src.utils.logger import logger

class YourSystemConnector:
    """Connector for Your System API"""

    def __init__(self):
        config = get_integration_config("yoursystem")
        self.api_key = config["api_key"]
        self.base_url = config["api_base_url"]
        self.client = httpx.AsyncClient(timeout=30.0)

    async def fetch_employees(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch employees from Your System"""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = await self.client.get(
            f"{self.base_url}/employees",
            headers=headers,
            params={"limit": limit}
        )
        response.raise_for_status()
        return response.json()

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
```

### 2. Add Configuration

Update `.env` and `src/core/config.py` with new integration credentials.

### 3. Create Workflow

Add workflow in `src/orchestration/workflows.py` for data sync.

---

## 📊 Monitoring & Observability

### Prometheus Metrics

Access metrics at: `http://localhost:8000/metrics`

Key metrics:
- Request count and latency
- Database query performance
- Job success/failure rates
- Integration health checks

### Grafana Dashboards

1. Access Grafana: http://localhost:3000
2. Login: `admin` / `admin`
3. Create dashboards using Prometheus datasource

### Logs

Structured logging with loguru:

```bash
# Follow logs
docker-compose logs -f mcp-server

# Filter by level
docker-compose logs mcp-server | grep ERROR
```

---

## 🧪 Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# View coverage
open htmlcov/index.html
```

---

## 🚢 Deployment

### Docker Production Build

```bash
# Build production image
docker build -t mcp-server:latest .

# Run container
docker run -d \
  --name mcp-server \
  -p 8000:8000 \
  --env-file .env.production \
  mcp-server:latest
```

### Terraform Deployment (AWS)

```bash
cd terraform/

# Initialize Terraform
terraform init

# Plan deployment
terraform plan -var-file="production.tfvars"

# Apply deployment
terraform apply -var-file="production.tfvars"
```

### Environment Variables (Production)

Ensure these are set:

- `ENVIRONMENT=production`
- `DEBUG=false`
- `SECRET_KEY=<strong-random-key>`
- `DATABASE_URL=<production-db-url>`
- All integration credentials

---

## 🔒 Security

### Best Practices

✅ Never commit `.env` files
✅ Rotate API keys regularly
✅ Use strong `SECRET_KEY` in production
✅ Enable HTTPS/TLS for all endpoints
✅ Implement rate limiting
✅ Monitor audit logs
✅ Use encrypted connections to databases

### Generating Secure Keys

```python
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate API Key
python -c "from src.core.security import generate_api_key; print(generate_api_key())"
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

[Your License Here]

---

## 🙋 Support

For issues and questions:
- Create an issue on GitHub
- Contact: [your-email@example.com]

---

## 🗺️ Roadmap

- [ ] Implement Temporal.io workflows
- [ ] Add gRPC endpoints
- [ ] Implement dbt data transformations
- [ ] Add comprehensive test coverage
- [ ] Create Terraform modules for AWS/Azure/GCP
- [ ] Add more integration connectors
- [ ] Implement real-time sync via WebSockets
- [ ] Add GraphQL API layer
- [ ] Implement data lineage tracking
- [ ] Add AI-powered mapping suggestions

---

**Built with ❤️ for AgentProvision by the DataFlow AI Team**
