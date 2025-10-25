# 🚀 Quick Start Guide - MCP Server

Get the MCP Server up and running in 5 minutes!

---

## Option 1: Docker Compose (Recommended)

The fastest way to get started:

```bash
# 1. Clone the repository (if you haven't)
cd /Users/jorgeaguilera/Documents/GitHub/AgentprovisionMCPserver

# 2. Copy environment file
cp .env.example .env

# 3. Start all services
make docker-up
# Or: docker-compose up -d

# 4. Wait for services to be ready (30 seconds)
# Check status:
docker-compose ps

# 5. Access the API
open http://localhost:8000/docs
```

### Verify Everything is Running

```bash
# Check health endpoint
curl http://localhost:8000/api/v1/health

# Expected response:
# {
#   "status": "healthy",
#   "version": "1.0.0",
#   "timestamp": "2024-...",
#   "services": { "api": "running" }
# }
```

### Access Services

| Service | URL | Credentials |
|---------|-----|-------------|
| API Documentation | http://localhost:8000/docs | - |
| API | http://localhost:8000/api/v1 | See below |
| Grafana | http://localhost:3000 | admin / admin |
| Prometheus | http://localhost:9091 | - |

---

## Option 2: Local Development (Python)

For active development:

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
make install
# Or: pip install -r requirements.txt

# 3. Start PostgreSQL and Redis
# You need these running separately or via Docker:
docker run -d --name mcp-postgres \
  -e POSTGRES_USER=mcpuser \
  -e POSTGRES_PASSWORD=mcppassword \
  -e POSTGRES_DB=mcpdb \
  -p 5432:5432 postgres:15-alpine

docker run -d --name mcp-redis \
  -p 6379:6379 redis:7-alpine

# 4. Copy and configure environment
cp .env.example .env
# Edit .env with your settings

# 5. Initialize database
make seed
# Or: python -m scripts.seed_db

# 6. Run development server
make dev
# Or: uvicorn src.api.main:app --reload
```

---

## 🧪 Testing the API

### Using the API Key (Test)

```bash
# Register a mapping
curl -X POST "http://localhost:8000/api/v1/mappings/register" \
  -H "X-API-Key: test-api-key-adp" \
  -H "Content-Type: application/json" \
  -d '{
    "source_system": "adp",
    "source_id": "EMP-99999",
    "source_entity_type": "employee",
    "target_system": "dentalerp",
    "target_id": "ERP-EMP-999",
    "target_entity_type": "employee",
    "confidence_score": 100
  }'

# List mappings
curl "http://localhost:8000/api/v1/mappings" \
  -H "X-API-Key: test-api-key-adp"

# Trigger a sync workflow
curl -X POST "http://localhost:8000/api/v1/workflows/run" \
  -H "X-API-Key: test-api-key-adp" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_type": "sync_employees",
    "source_system": "adp",
    "target_system": "dentalerp",
    "entity_type": "employee",
    "config": {
      "batch_size": 50
    }
  }'
```

### Using Swagger UI

1. Open http://localhost:8000/docs
2. Click "Authorize" button
3. Enter API Key: `test-api-key-adp`
4. Try the endpoints interactively!

---

## 📊 View Metrics & Logs

### Check Logs

```bash
# All services
docker-compose logs -f

# Just the API
make docker-logs
# Or: docker-compose logs -f mcp-server

# Database logs
docker-compose logs -f postgres
```

### Prometheus Metrics

1. Open http://localhost:9091
2. Try queries:
   - `up` - Service health
   - `http_requests_total` - Request count
   - `http_request_duration_seconds` - Request latency

### Grafana Dashboards

1. Open http://localhost:3000
2. Login: admin / admin
3. Add visualizations from Prometheus data source

---

## 🛑 Stopping Services

```bash
# Stop all services
make docker-down
# Or: docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v
```

---

## 🔧 Common Issues

### Port Already in Use

```bash
# Check what's using port 8000
lsof -i :8000

# Change port in docker-compose.yml:
ports:
  - "8001:8000"  # Use 8001 instead
```

### Database Connection Failed

```bash
# Wait longer for PostgreSQL to start
docker-compose logs postgres

# Restart just the API
docker-compose restart mcp-server
```

### Permission Errors

```bash
# Fix permissions on logs directory
chmod -R 755 logs/
```

---

## 📚 Next Steps

1. **Read the full README**: [README.md](README.md)
2. **Explore API endpoints**: http://localhost:8000/docs
3. **Add integrations**: See [README.md](README.md#-adding-new-integrations)
4. **Configure production**: Edit `.env` with real credentials
5. **Deploy to AWS**: Use Terraform configs in `terraform/`

---

## 💡 Helpful Commands

```bash
# See all available commands
make help

# Run tests
make test

# Check code quality
make lint

# Format code
make format

# Seed database with sample data
make seed

# View database migrations
alembic history

# Create new migration
make migrate-create
```

---

## 🆘 Getting Help

- Check logs: `make docker-logs`
- API Documentation: http://localhost:8000/docs
- Health check: `curl localhost:8000/api/v1/health`
- Review README.md for detailed documentation

---

**Happy coding! 🎉**
