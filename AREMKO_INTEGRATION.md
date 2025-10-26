# 🏨 Guía Completa de Integración: Aremko + MCP Server

**Sistema de Orquestación de Datos para Spa & Wellness Center**

---

## 📋 Tabla de Contenidos

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Problema](#problema)
3. [Solución](#solución)
4. [Arquitectura](#arquitectura)
5. [Conectores Implementados](#conectores-implementados)
6. [API Endpoints](#api-endpoints)
7. [Casos de Uso](#casos-de-uso)
8. [Setup e Instalación](#setup-e-instalación)
9. [Testing](#testing)
10. [Despliegue](#despliegue)
11. [Roadmap](#roadmap)

---

## 🎯 Resumen Ejecutivo

**Aremko** (www.aremko.cl) es un Spa & Wellness Center con servicios de:
- 💆 Masajes terapéuticos y relajantes
- 🛁 Tinas calientes
- 🏠 Alojamientos
- 🧴 Venta de productos (aceites, cremas, cosméticos)

### El Desafío

Los datos de clientes están **fragmentados** en múltiples fuentes:
- ✅ **Base de datos actual** (Django/PostgreSQL) - operacional desde 2020
- 📁 **Archivos legacy** (CSV de sistema antiguo 2015-2020)
- ❌ **Sin vista unificada** del cliente
- ❌ **Sin análisis de comportamiento**
- ❌ **Marketing genérico** sin personalización

### La Oportunidad

Cliente inactivo contacta → Necesitamos:
1. **Identificar** al cliente en ambas fuentes
2. **Unificar** su historial completo
3. **Analizar** su comportamiento y preferencias
4. **Generar** propuesta personalizada con IA
5. **Reactivar** con ofertas relevantes

---

## 🚀 Solución: MCP Server como Orquestador

El **MCP Server** actúa como **capa de orquestación** que:

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP SERVER (Orchestrator)                │
│                                                             │
│  ┌──────────────┐  ┌───────────────┐  ┌─────────────────┐ │
│  │ DB Connector │  │Legacy Connector│  │Analytics Engine │ │
│  └──────┬───────┘  └───────┬───────┘  └────────┬────────┘ │
│         │                  │                    │          │
└─────────┼──────────────────┼────────────────────┼──────────┘
          │                  │                    │
          ▼                  ▼                    ▼
   ┌────────────┐    ┌──────────────┐    ┌─────────────┐
   │  Aremko DB │    │ Legacy CSV   │    │ RFM Analysis│
   │(PostgreSQL)│    │(Clientes.csv)│    │  Segments   │
   └────────────┘    └──────────────┘    └─────────────┘
```

### Flujo de Trabajo

```
1. Cliente antiguo llama: "Hola, soy María González"

2. MCP busca en ambas fuentes → Encuentra match

3. Orquesta datos:
   - Reservas actuales (2020-2024)
   - Reservas legacy (2015-2020)
   - Total visitas: 17
   - Total gastado: $680.000 CLP

4. Analiza comportamiento:
   - RFM Score: R=1 (inactivo), F=4 (frecuente), M=3 (buen gastador)
   - Segmento: "At Risk" (era buena cliente, ahora inactiva)
   - Servicios preferidos: Masaje relajante (12x), Tina caliente (5x)
   - Presupuesto promedio: $40.000 por visita

5. IA genera propuesta personalizada:
   "Hola María! Te extrañamos en Aremko 💙
   Tu último masaje relajante fue hace 4 años...

   Oferta especial para ti:
   🎁 Pack Relajación Total: $42.000
      ✓ Masaje relajante 60min (tu favorito!)
      ✓ Tina caliente 30min
      ✓ Aceite esencial de regalo
      ✓ 15% descuento reactivación"
```

---

## 🏗️ Arquitectura del Sistema

### Componentes Principales

#### 1. **Database Connector** (`aremko_db_connector.py`)
- Conecta con PostgreSQL de Django (BD actual)
- Acceso asíncrono con `asyncpg`
- Fetch de clientes, reservas, servicios, productos, pagos
- Queries optimizadas para analytics

**Modelos Django que consume:**
```python
# ventas/models.py
class Cliente:
    nombre, email, telefono, documento_identidad, pais, ciudad

class VentaReserva:
    cliente, servicios (ManyToMany), productos (ManyToMany)
    total, pagado, saldo_pendiente, estado_pago
    fecha_creacion, fecha_reserva

class Servicio:
    nombre, precio_base, duracion, tipo_servicio
    (tina, masaje, cabana, otro)

class Pago:
    venta_reserva, monto, metodo_pago, fecha_pago
```

#### 2. **Legacy Connector** (`aremko_legacy_connector.py`)
- Lee archivo CSV: `Clientes-2024-06-23-16-31-48.csv`
- Parsea y normaliza datos históricos
- Fuzzy matching para encontrar duplicados
- Maneja formatos inconsistentes (fechas, teléfonos, nombres)

**Estructura CSV Legacy:**
```csv
Auto Increment,Record ID,Created On,Email,Telefono,Reservas,Client,Documento Identidad,Direccion,voucher
1657,VX9QoGpQwY,2/25/2020 18:05,,984280796,,sonia silva 984280796,,Santiago RM,
```

**Normalización automática:**
- ✅ Nombres: "sonia silva 984280796" → "Sonia Silva"
- ✅ Teléfonos: "984280796" → "+56984280796"
- ✅ Emails: validación y lowercase
- ✅ Ubicación: "Santiago, RM" → ciudad="Santiago", region="RM"

#### 3. **Analytics Connector** (`aremko_analytics_connector.py`)
- Análisis RFM (Recency, Frequency, Monetary)
- Segmentación automática de clientes
- Perfiles 360° unificados
- Insights de comportamiento

**Segmentos RFM:**
- **VIP**: Recent, frequent, high spender (R≥4, F≥4, M≥4)
- **Champions**: Top customers (R≥4, F≥3, M≥3)
- **Loyal**: Frequent visitors (F≥4, M≥3)
- **Promising**: Recent, low frequency (R≥4, F≤2)
- **At Risk**: Was good, now inactive (R≤2, F≥3, M≥3)
- **Hibernating**: Long-time inactive (R=1, F≥2)
- **Lost**: Very inactive (R≤1)
- **New**: Recent, few visits (R≥4, F≤2)
- **Occasional**: Everything else

#### 4. **Mapping Registry** (MCP Core)
- Vincula IDs entre legacy y actual
- Confidence scores (0-100)
- Bidirectional lookups
- Audit trail completo

---

## 🔌 Conectores Implementados

### 1. Aremko DB Connector

**Capabilities:**

```python
# Initialize
db = AremkoDBConnector(tenant="aremko")
await db.connect()

# Fetch customers
customers = await db.fetch_customers(limit=100, filters={'telefono': '987654321'})

# Search customer
matches = await db.find_customer_by_identifier("María González")

# Get customer stats
stats = await db.get_customer_stats(customer_id=123)
# Returns:
# {
#   "total_visitas": 17,
#   "total_gastado": 680000.0,
#   "promedio_por_visita": 40000.0,
#   "ultima_visita": datetime(...),
#   "primera_visita": datetime(...),
#   "visitas_ultimo_ano": 2
# }

# Get service preferences
prefs = await db.get_customer_service_preferences(customer_id=123)
# Returns top 10 services by frequency

# Get inactive customers
inactive = await db.get_inactive_customers(months=12)

await db.close()
```

### 2. Aremko Legacy Connector

**Capabilities:**

```python
# Initialize
legacy = AremkoLegacyConnector(tenant="aremko")

# Fetch all legacy customers
customers = await legacy.fetch_legacy_customers(limit=100)

# Search legacy customer
matches = await legacy.find_legacy_customer_by_identifier("María")

# Get legacy stats
stats = await legacy.get_legacy_stats()
# Returns:
# {
#   "total_customers": 2847,
#   "with_email": 1234,
#   "with_phone": 2801,
#   "email_percentage": 43.3,
#   "phone_percentage": 98.4,
#   "top_cities": [("Puerto Montt", 456), ("Santiago", 234)],
#   "date_range": {"earliest": "2015-01-05", "latest": "2020-06-23"}
# }

# Find potential matches
current_customers = await db.fetch_customers(limit=1000)
matches = await legacy.find_potential_matches_in_current(
    legacy_customer,
    current_customers
)
# Returns confidence scores and match reasons
```

### 3. Aremko Analytics Connector

**Capabilities:**

```python
# Initialize
analytics = AremkoAnalyticsConnector(tenant="aremko")

# Generate 360° profile
profile = await analytics.generate_customer_360_profile(
    customer_id=123,
    include_legacy=True
)
# Returns:
# {
#   "customer_id": 123,
#   "basic_info": {...},
#   "statistics": {...},
#   "rfm_analysis": {
#     "recency_score": 1,
#     "frequency_score": 4,
#     "monetary_score": 3,
#     "rfm_combined_score": 2.7,
#     "days_since_last_visit": 1460,
#     "segment": "At Risk"
#   },
#   "service_preferences": [...],
#   "recent_reservations": [...],
#   "legacy_data": {...}
# }

# Analyze behavior
insights = await analytics.analyze_customer_behavior(profile)
# Returns:
# {
#   "segment": "At Risk",
#   "ltv": 680000.0,
#   "avg_ticket": 40000.0,
#   "visit_frequency": "Regular (cada 2 meses)",
#   "preferred_services": ["Masaje relajante", "Tina caliente"],
#   "preferred_service_types": ["masaje", "tina"],
#   "seasonality": {
#     "pattern": "Prefiere verano",
#     "best_months": ["Enero", "Febrero", "Diciembre"]
#   },
#   "churn_risk": "Alto",
#   "upsell_potential": "Alto (probar nuevos servicios)"
# }

# Batch analysis for campaigns
results = await analytics.batch_analyze_inactive_customers(
    months=12,
    limit=100
)

await analytics.db_connector.close()
```

---

## 📡 API Endpoints

Base URL: `http://localhost:8000/api/v1/aremko`

### Customer Lookup

#### `GET /customers/search`

Buscar clientes en múltiples fuentes.

**Query Parameters:**
- `query` (required): Nombre, teléfono, email, o RUT
- `source` (optional): `current`, `legacy`, o `all` (default: `current`)

**Headers:**
- `X-API-Key`: Your API key
- `X-Tenant`: `aremko`

**Response:**
```json
{
  "query": "María González",
  "source": "all",
  "current_matches": [
    {
      "id": 123,
      "nombre": "María González",
      "telefono": "+56987654321",
      "email": "maria@gmail.com"
    }
  ],
  "legacy_matches": [
    {
      "legacy_id": "1657",
      "record_id": "VX9QoGpQwY",
      "nombre": "María González",
      "telefono": "+56987654321"
    }
  ]
}
```

#### `GET /customers/{customer_id}/profile`

Obtener perfil 360° completo.

**Path Parameters:**
- `customer_id`: ID del cliente en BD actual

**Query Parameters:**
- `include_legacy` (optional): `true`/`false` (default: `true`)

**Response:**
```json
{
  "customer_id": 123,
  "basic_info": {
    "id": 123,
    "nombre": "María González",
    "email": "maria@gmail.com",
    "telefono": "+56987654321",
    "documento_identidad": "12345678-9",
    "ciudad": "Puerto Montt",
    "pais": "Chile"
  },
  "statistics": {
    "total_visitas": 17,
    "total_gastado": 680000.0,
    "promedio_por_visita": 40000.0,
    "ultima_visita": "2020-03-15T14:30:00",
    "primera_visita": "2016-08-20T11:00:00",
    "visitas_ultimo_ano": 0
  },
  "rfm_analysis": {
    "recency_score": 1,
    "frequency_score": 4,
    "monetary_score": 3,
    "rfm_combined_score": 2.7,
    "days_since_last_visit": 1460,
    "segment": "At Risk"
  },
  "service_preferences": [
    {
      "servicio_id": 5,
      "servicio_nombre": "Masaje Relajante",
      "tipo_servicio": "masaje",
      "veces_reservado": 12,
      "ultima_reserva": "2020-03-15T15:00:00"
    },
    {
      "servicio_id": 8,
      "servicio_nombre": "Tina Caliente Premium",
      "tipo_servicio": "tina",
      "veces_reservado": 5,
      "ultima_reserva": "2020-02-10T16:30:00"
    }
  ],
  "recent_reservations": [...],
  "recent_payments": [...],
  "legacy_data": {...}
}
```

#### `GET /customers/{customer_id}/insights`

Obtener análisis de comportamiento e insights.

**Response:**
```json
{
  "customer_id": 123,
  "segment": "At Risk",
  "ltv": 680000.0,
  "avg_ticket": 40000.0,
  "visit_frequency": "Regular (cada 2 meses)",
  "preferred_services": [
    "Masaje Relajante",
    "Tina Caliente Premium"
  ],
  "preferred_service_types": ["masaje", "tina"],
  "seasonality": {
    "pattern": "Prefiere verano",
    "best_months": ["Enero", "Febrero", "Diciembre"],
    "month_counts": {
      "Enero": 4,
      "Febrero": 3,
      "Diciembre": 2
    }
  },
  "payment_behavior": {
    "preferred_method": "transferencia",
    "payment_methods_used": ["transferencia", "efectivo", "flow"],
    "method_distribution": {
      "transferencia": 10,
      "efectivo": 5,
      "flow": 2
    }
  },
  "churn_risk": "Alto",
  "upsell_potential": "Alto (probar nuevos servicios)"
}
```

### Campaigns & Reactivation

#### `GET /campaigns/inactive-customers`

Obtener clientes inactivos con análisis completo para campañas.

**Query Parameters:**
- `months` (optional): Meses de inactividad (default: 12, min: 1, max: 36)
- `limit` (optional): Máximo de clientes (default: 100, min: 1, max: 500)

**Response:**
```json
{
  "total_analyzed": 87,
  "parameters": {
    "months_inactive": 12,
    "limit": 100
  },
  "customers": [
    {
      "profile": {...},
      "insights": {...},
      "reactivation_priority": 85
    }
  ]
}
```

**Priority Score** (0-100):
- **80-100**: Alta prioridad (VIP/Champions inactivos, alto LTV)
- **60-79**: Media prioridad (Loyal/At Risk, LTV medio)
- **0-59**: Baja prioridad (Lost, LTV bajo)

#### `GET /campaigns/segments/{segment}`

Obtener clientes por segmento RFM.

**Path Parameters:**
- `segment`: VIP, Champions, Loyal, Promising, At Risk, Hibernating, Lost, New, Occasional

**Query Parameters:**
- `limit` (optional): Máximo de clientes (default: 100)

**Response:**
```json
{
  "segment": "At Risk",
  "total_found": 23,
  "customers": [
    {
      "customer": {...},
      "stats": {...},
      "rfm": {...}
    }
  ]
}
```

### Data Synchronization

#### `POST /sync/legacy-to-current`

Sincronizar datos legacy con BD actual (crear mappings).

**Query Parameters:**
- `limit` (optional): Límite de registros a sincronizar

**Response:**
```json
{
  "total_legacy": 2847,
  "total_current": 1234,
  "mappings_created": 856,
  "high_confidence": 723,
  "medium_confidence": 133,
  "no_match": 1991,
  "details": [
    {
      "legacy_id": "1657",
      "legacy_name": "María González",
      "current_id": 123,
      "current_name": "María González",
      "confidence": 95,
      "reasons": ["phone_exact", "name_exact"]
    }
  ]
}
```

#### `GET /mappings/customer/{customer_id}`

Obtener mappings para un cliente específico.

**Response:**
```json
{
  "customer_id": 123,
  "has_legacy_data": true,
  "mapping": {
    "id": "uuid-here",
    "legacy_id": "1657",
    "confidence_score": 95,
    "created_at": "2024-10-26T10:30:00",
    "metadata": {
      "match_reasons": ["phone_exact", "name_exact"],
      "legacy_name": "María González",
      "current_name": "María González"
    }
  },
  "legacy_customer": {...}
}
```

### Statistics

#### `GET /stats/overview`

Obtener estadísticas generales de Aremko.

**Response:**
```json
{
  "current_database": {
    "total_customers": 1234,
    "inactive_12_months": 234,
    "services_available": 15,
    "products_available": 45
  },
  "legacy_data": {
    "total_customers": 2847,
    "with_email": 1234,
    "with_phone": 2801,
    "email_percentage": 43.3,
    "phone_percentage": 98.4,
    "top_cities": [
      ["Puerto Montt", 456],
      ["Santiago", 234]
    ]
  },
  "data_completeness": {
    "current_with_email": 1100,
    "current_with_phone": 1234,
    "current_with_rut": 890
  }
}
```

---

## 💡 Casos de Uso

### Caso 1: Cliente Inactivo Llama al Spa

**Escenario:**
María González llama después de 4 años sin venir.

**Flujo:**

```bash
# 1. Recepcionista busca cliente
curl -X GET "http://localhost:8000/api/v1/aremko/customers/search?query=Maria+Gonzalez&source=all" \
  -H "X-API-Key: your-api-key" \
  -H "X-Tenant: aremko"

# 2. Obtener perfil completo
curl -X GET "http://localhost:8000/api/v1/aremko/customers/123/profile?include_legacy=true" \
  -H "X-API-Key: your-api-key" \
  -H "X-Tenant: aremko"

# 3. Obtener insights
curl -X GET "http://localhost:8000/api/v1/aremko/customers/123/insights" \
  -H "X-API-Key: your-api-key" \
  -H "X-Tenant: aremko"
```

**Resultado:**
- ✅ Identificación instantánea (2 segundos)
- ✅ Historial completo 2015-2020 (legacy) + 2020-2024 (actual)
- ✅ Insights: "At Risk", servicios favoritos, presupuesto promedio
- ✅ Propuesta personalizada lista

### Caso 2: Campaña de Reactivación Masiva

**Escenario:**
Marketing quiere reactivar clientes inactivos de alto valor.

**Flujo:**

```bash
# Obtener top 100 clientes inactivos priorizados
curl -X GET "http://localhost:8000/api/v1/aremko/campaigns/inactive-customers?months=12&limit=100" \
  -H "X-API-Key: your-api-key" \
  -H "X-Tenant: aremko"
```

**Resultado:**
```json
{
  "total_analyzed": 87,
  "customers": [
    {
      "reactivation_priority": 92,
      "profile": {
        "customer_id": 456,
        "basic_info": {
          "nombre": "Patricio López",
          "email": "patricio@gmail.com"
        },
        "statistics": {
          "total_gastado": 1200000.0,
          "total_visitas": 25
        },
        "rfm_analysis": {
          "segment": "At Risk",
          "days_since_last_visit": 450
        }
      },
      "insights": {
        "ltv": 1200000.0,
        "preferred_services": ["Masaje Terapéutico", "Alojamiento Weekend"],
        "churn_risk": "Medio-Alto",
        "upsell_potential": "Bajo (ya es buen cliente)"
      }
    }
  ]
}
```

**Acción:**
1. Ordenar por `reactivation_priority` (ya viene ordenado)
2. Para cada cliente:
   - Generar email personalizado con IA
   - Incluir servicios favoritos
   - Ofrecer descuento basado en LTV
   - Mencionar tiempo sin venir
3. Enviar campaña segmentada

### Caso 3: Análisis de Segmentos para Estrategia

**Escenario:**
Gerencia quiere entender composición de clientes.

**Flujo:**

```bash
# VIP Customers
curl -X GET "http://localhost:8000/api/v1/aremko/campaigns/segments/VIP?limit=50" \
  -H "X-API-Key: your-api-key" \
  -H "X-Tenant: aremko"

# At Risk Customers
curl -X GET "http://localhost:8000/api/v1/aremko/campaigns/segments/At%20Risk?limit=100" \
  -H "X-API-Key: your-api-key" \
  -H "X-Tenant: aremko"

# Lost Customers
curl -X GET "http://localhost:8000/api/v1/aremko/campaigns/segments/Lost?limit=200" \
  -H "X-API-Key: your-api-key" \
  -H "X-Tenant: aremko"
```

**Insights:**
- Número de clientes por segmento
- LTV promedio por segmento
- Servicios más populares por segmento
- Estacionalidad por segmento

### Caso 4: Sincronización Inicial Legacy → Actual

**Escenario:**
Primera vez configurando el sistema.

**Flujo:**

```bash
# Sincronizar todos los datos legacy
curl -X POST "http://localhost:8000/api/v1/aremko/sync/legacy-to-current" \
  -H "X-API-Key: your-api-key" \
  -H "X-Tenant: aremko"
```

**Proceso:**
1. Lee 2,847 clientes legacy del CSV
2. Fetch 1,234 clientes actuales de PostgreSQL
3. Fuzzy matching por:
   - Teléfono (peso: 90%)
   - Email (peso: 85%)
   - RUT (peso: 95%)
   - Nombre (peso: 50-70%)
4. Crea mappings con confidence score
5. Retorna estadísticas

**Resultado:**
- ✅ 856 mappings creados
- ✅ 723 high confidence (≥85%)
- ✅ 133 medium confidence (70-84%)
- ❌ 1,991 sin match (clientes únicos de legacy)

---

## ⚙️ Setup e Instalación

### Prerequisitos

- Python 3.11+
- PostgreSQL 15+
- Git
- Acceso a base de datos Aremko
- Archivo CSV legacy en path accesible

### 1. Clonar MCP Server

```bash
cd /Users/jorgeaguilera/Documents/GitHub/
git clone <mcp-server-repo-url>
cd AgentprovisionMCPserver
```

### 2. Crear Entorno Virtual

```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate  # Windows
```

### 3. Instalar Dependencias

```bash
pip install -r requirements.txt

# Adicional para Aremko (asyncpg)
pip install asyncpg
```

### 4. Configurar Variables de Entorno

Crear archivo `.env`:

```bash
cp .env.example .env
nano .env
```

**Configurar Aremko:**

```env
# Database Aremko
AREMKO_DATABASE_URL=postgresql+asyncpg://aremko_user:password@localhost:5432/aremko_db

# Legacy Data Path
AREMKO_LEGACY_DATA_PATH=/Users/jorgeaguilera/Documents/GitHub/booking-system-aremko

# MCP Database
DATABASE_URL=postgresql+asyncpg://mcpuser:mcppassword@localhost:5432/mcpdb

# API Key
SECRET_KEY=your-secret-key-here

# Optional: Claude AI
ANTHROPIC_API_KEY=your-anthropic-key
```

### 5. Inicializar Base de Datos MCP

```bash
# Aplicar migraciones
python -m scripts.init_db

# O manualmente
python
>>> from src.db.database import init_db
>>> import asyncio
>>> asyncio.run(init_db())
```

### 6. Ejecutar Servidor

```bash
# Development
python src/api/main.py

# O con uvicorn
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 7. Verificar Instalación

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Aremko stats
curl -X GET "http://localhost:8000/api/v1/aremko/stats/overview" \
  -H "X-API-Key: your-api-key" \
  -H "X-Tenant: aremko"
```

---

## 🧪 Testing

### Test 1: Conexión BD Aremko

```python
import asyncio
from src.integrations.aremko_db_connector import AremkoDBConnector

async def test_db():
    db = AremkoDBConnector(tenant="aremko")
    customers = await db.fetch_customers(limit=10)
    print(f"Fetched {len(customers)} customers")
    for c in customers:
        print(f"  - {c['nombre']} ({c['telefono']})")
    await db.close()

asyncio.run(test_db())
```

### Test 2: Lectura Legacy CSV

```python
import asyncio
from src.integrations.aremko_legacy_connector import AremkoLegacyConnector

async def test_legacy():
    legacy = AremkoLegacyConnector(tenant="aremko")
    customers = await legacy.fetch_legacy_customers(limit=10)
    print(f"Fetched {len(customers)} legacy customers")

    stats = await legacy.get_legacy_stats()
    print(f"Total legacy: {stats['total_customers']}")
    print(f"With email: {stats['email_percentage']:.1f}%")

asyncio.run(test_legacy())
```

### Test 3: RFM Analysis

```python
import asyncio
from src.integrations.aremko_analytics_connector import AremkoAnalyticsConnector

async def test_analytics():
    analytics = AremkoAnalyticsConnector(tenant="aremko")

    # Generate profile for customer ID 1
    profile = await analytics.generate_customer_360_profile(1, include_legacy=True)

    print(f"Customer: {profile['basic_info']['nombre']}")
    print(f"Segment: {profile['rfm_analysis']['segment']}")
    print(f"LTV: ${profile['statistics']['total_gastado']:,.0f} CLP")

    await analytics.db_connector.close()

asyncio.run(test_analytics())
```

### Test 4: API Endpoints

```bash
# Search customer
curl -X GET "http://localhost:8000/api/v1/aremko/customers/search?query=987654321" \
  -H "X-API-Key: test-key"

# Get profile
curl -X GET "http://localhost:8000/api/v1/aremko/customers/1/profile" \
  -H "X-API-Key: test-key"

# Sync legacy
curl -X POST "http://localhost:8000/api/v1/aremko/sync/legacy-to-current?limit=10" \
  -H "X-API-Key: test-key"
```

---

## 🚀 Despliegue

### Opción A: Render.com (Recomendado)

1. **Push código a GitHub**
```bash
git add .
git commit -m "feat(aremko): add complete integration"
git push origin main
```

2. **Crear servicio en Render**
- Connect GitHub repo
- Web Service → Docker
- Environment variables:
  - `AREMKO_DATABASE_URL` (usar Render PostgreSQL URL)
  - `DATABASE_URL` (MCP PostgreSQL)
  - `SECRET_KEY`
  - All other vars from `.env`

3. **Deploy**
- Render builds Docker image
- Automatic deployments on push

### Opción B: AWS ECS (Terraform)

```bash
cd terraform/
terraform init
terraform plan -var-file="aremko.tfvars"
terraform apply
```

### Opción C: Docker Compose (Local/Server)

```bash
docker-compose up -d
```

---

## 📈 Roadmap

### Fase 1: Foundation ✅ COMPLETADA
- [x] DB Connector para Aremko PostgreSQL
- [x] Legacy Connector para CSV
- [x] Analytics Connector con RFM
- [x] API Endpoints completos
- [x] Documentación

### Fase 2: AI Integration (En Progreso)
- [ ] Conector Claude AI
- [ ] Generación automática de propuestas
- [ ] Templates de emails personalizados
- [ ] A/B testing de mensajes

### Fase 3: Automation
- [ ] Campañas automáticas programadas
- [ ] Webhooks para eventos de Aremko
- [ ] Integración con sistema de emails (Mailgun/SendGrid)
- [ ] Dashboard de métricas

### Fase 4: Advanced Analytics
- [ ] Predicción de churn con ML
- [ ] Recomendaciones de servicios con collaborative filtering
- [ ] Análisis de sentiment de comentarios
- [ ] Clustering avanzado de clientes

---

## 🎯 KPIs y Métricas

### Métricas de Negocio

- **Tasa de Reactivación**: % de clientes inactivos que regresan
  - **Target**: 15-25% en primeros 3 meses
- **LTV Incremento**: Aumento en valor de vida del cliente
  - **Target**: +30% para reactivados
- **Conversión de Ofertas**: % de propuestas aceptadas
  - **Target**: 25-40% con personalización
- **Reducción de Churn**: % menos clientes perdidos
  - **Target**: -50% en segmento "At Risk"

### Métricas Técnicas

- **Latencia de Lookup**: Tiempo de búsqueda de cliente
  - **Actual**: < 2 segundos
- **Accuracy de Matching**: % de mappings correctos
  - **Target**: > 90% confidence
- **Cobertura de Datos**: % clientes con historial completo
  - **Actual**: ~30% tienen datos legacy + actual

---

## 🤝 Soporte

Para dudas o issues:
- **Email**: jorge@aremko.cl
- **GitHub Issues**: [Crear issue](https://github.com/your-repo/issues)

---

**¡Aremko + MCP Server = Marketing Personalizado a Escala!** 🏨✨
