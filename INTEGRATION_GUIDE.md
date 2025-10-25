# 🔌 Guía de Integración Práctica

## Cómo Conectar TalleresIA y Eunacom con el MCP Server

Esta guía te muestra **paso a paso** cómo integrar tu proyecto existente con el MCP Server.

---

## 🎯 ¿Qué Vamos a Hacer?

### Escenario Real: TalleresIA

Tu usuario visita **talleresia-frontend.vercel.app**, se registra en un taller y paga con Stripe.

**ANTES** (sin MCP):
```typescript
// En tu código de TalleresIA tendrías que hacer:
- Llamar API de Stripe directamente
- Guardar en tu base de datos
- Enviar email manualmente
- Agregar a Mailchimp manualmente
- Crear meeting en Zoom manualmente
- TODO el código de integración en tu frontend/backend
```

**AHORA** (con MCP):
```typescript
// Una sola llamada al MCP Server:
const response = await fetch('https://mcp.tudominio.com/api/v1/payments/create-intent', {
  method: 'POST',
  headers: {
    'X-API-Key': 'tu-api-key-talleresia',
    'X-Tenant': 'talleresia',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    amount: 5000,  // $50.00
    currency: 'usd',
    customer_email: 'alumno@example.com',
    description: 'Taller IA Básico 2024'
  })
});

// ¡Y el MCP se encarga del resto!
```

---

## 📋 PASO 1: Preparar el MCP Server

### 1.1 Iniciar el MCP Server Localmente

```bash
cd /Users/jorgeaguilera/Documents/GitHub/AgentprovisionMCPserver

# Copiar environment
cp .env.example .env

# Editar .env con tus credenciales reales
nano .env
```

### 1.2 Configurar Credenciales en .env

```bash
# ===========================================
# Configuración para TalleresIA
# ===========================================

# API Key para TalleresIA (generar una nueva)
# Este key lo usarás en tu frontend/backend
TALLERESIA_API_KEY=mcp_talleresia_secret_abc123xyz

# Stripe para TalleresIA
STRIPE_SECRET_KEY_TALLERESIA=sk_test_51ABC...tu_key_de_stripe
STRIPE_PUBLISHABLE_KEY_TALLERESIA=pk_test_51DEF...tu_public_key

# Mailchimp para TalleresIA (próximo paso)
MAILCHIMP_API_KEY_TALLERESIA=tu_mailchimp_key
MAILCHIMP_LIST_ID_TALLERESIA=tu_lista_id

# Zoom para TalleresIA (próximo paso)
ZOOM_API_KEY_TALLERESIA=tu_zoom_api_key
ZOOM_API_SECRET_TALLERESIA=tu_zoom_secret
```

### 1.3 Iniciar el Servidor

```bash
# Con Docker (recomendado)
make docker-up

# O localmente
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
make seed  # Crear tablas
make dev   # Iniciar servidor
```

Servidor corriendo en: **http://localhost:8000**

---

## 📋 PASO 2: Conectar desde TalleresIA Frontend

### 2.1 Estructura de tu Proyecto TalleresIA

```
talleresia-frontend/  (tu proyecto en Vercel)
├── src/
│   ├── lib/
│   │   └── mcp-client.ts          👈 CREAR ESTE ARCHIVO
│   ├── app/
│   │   └── checkout/
│   │       └── page.tsx            👈 MODIFICAR ESTE ARCHIVO
│   └── components/
│       └── PaymentForm.tsx         👈 USAR MCP AQUÍ
└── .env.local                      👈 CONFIGURAR AQUÍ
```

### 2.2 Crear Cliente MCP (lib/mcp-client.ts)

```typescript
// src/lib/mcp-client.ts

const MCP_API_URL = process.env.NEXT_PUBLIC_MCP_API_URL || 'http://localhost:8000/api/v1';
const MCP_API_KEY = process.env.NEXT_PUBLIC_MCP_API_KEY;
const TENANT = 'talleresia';

export interface PaymentIntentRequest {
  amount: number;  // En centavos
  currency: string;
  customer_email: string;
  customer_name?: string;
  description?: string;
  metadata?: Record<string, any>;
}

export interface PaymentIntentResponse {
  payment_intent_id: string;
  client_secret: string;
  amount: number;
  currency: string;
  status: string;
}

class MCPClient {
  private baseURL: string;
  private apiKey: string;
  private tenant: string;

  constructor(baseURL: string, apiKey: string, tenant: string) {
    this.baseURL = baseURL;
    this.apiKey = apiKey;
    this.tenant = tenant;
  }

  /**
   * Crear un payment intent con Stripe a través del MCP Server
   */
  async createPaymentIntent(
    request: PaymentIntentRequest
  ): Promise<PaymentIntentResponse> {
    const response = await fetch(`${this.baseURL}/payments/create-intent`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': this.apiKey,
        'X-Tenant': this.tenant,
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Error creating payment intent');
    }

    return response.json();
  }

  /**
   * Consultar el estado de un pago
   */
  async getPaymentStatus(paymentIntentId: string) {
    const response = await fetch(
      `${this.baseURL}/payments/${paymentIntentId}`,
      {
        headers: {
          'X-API-Key': this.apiKey,
          'X-Tenant': this.tenant,
        },
      }
    );

    if (!response.ok) {
      throw new Error('Error fetching payment status');
    }

    return response.json();
  }

  /**
   * Trigger un workflow completo (pago + email + zoom + etc)
   */
  async triggerEnrollmentWorkflow(data: {
    student_email: string;
    taller_id: string;
    payment_id: string;
  }) {
    const response = await fetch(`${this.baseURL}/workflows/run`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': this.apiKey,
        'X-Tenant': this.tenant,
      },
      body: JSON.stringify({
        workflow_type: 'enroll_student',
        source_system: 'talleresia',
        target_system: 'multiple',
        entity_type: 'enrollment',
        config: {
          student_email: data.student_email,
          taller_id: data.taller_id,
          payment_id: data.payment_id,
          integrations: ['stripe', 'mailchimp', 'zoom', 'calendar', 'email'],
        },
      }),
    });

    if (!response.ok) {
      throw new Error('Error triggering workflow');
    }

    return response.json();
  }
}

// Exportar instancia configurada
export const mcpClient = new MCPClient(
  MCP_API_URL,
  MCP_API_KEY!,
  TENANT
);
```

### 2.3 Configurar Variables de Entorno (.env.local)

```bash
# En tu proyecto talleresia-frontend/.env.local

# MCP Server Configuration
NEXT_PUBLIC_MCP_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_MCP_API_KEY=mcp_talleresia_secret_abc123xyz

# O en producción:
# NEXT_PUBLIC_MCP_API_URL=https://mcp.tudominio.com/api/v1
```

### 2.4 Usar en tu Componente de Checkout

```typescript
// src/app/checkout/page.tsx

'use client';

import { useState } from 'react';
import { mcpClient } from '@/lib/mcp-client';

export default function CheckoutPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handlePurchase(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      // 1. Crear payment intent en MCP Server
      const paymentIntent = await mcpClient.createPaymentIntent({
        amount: 5000, // $50.00 en centavos
        currency: 'usd',
        customer_email: 'alumno@example.com',
        customer_name: 'Juan Pérez',
        description: 'Taller de IA Básico 2024',
        metadata: {
          taller_id: 'taller-ia-basico-2024',
          taller_name: 'IA Básico',
        },
      });

      console.log('Payment Intent created:', paymentIntent);

      // 2. Aquí usarías Stripe Elements para completar el pago
      // (usando el client_secret que devolvió el MCP)

      // 3. Una vez el pago sea exitoso, trigger el workflow completo
      await mcpClient.triggerEnrollmentWorkflow({
        student_email: 'alumno@example.com',
        taller_id: 'taller-ia-basico-2024',
        payment_id: paymentIntent.payment_intent_id,
      });

      // 4. ¡Listo! El MCP se encarga de:
      // - Confirmar pago
      // - Enviar email de bienvenida
      // - Agregar a Mailchimp
      // - Crear meeting en Zoom
      // - Agregar a Google Calendar
      // - etc.

      alert('¡Pago exitoso! Revisa tu email.');
    } catch (err: any) {
      setError(err.message);
      console.error('Error:', err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container mx-auto p-8">
      <h1 className="text-3xl font-bold mb-4">Checkout</h1>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      <form onSubmit={handlePurchase}>
        <button
          type="submit"
          disabled={loading}
          className="bg-blue-500 text-white px-6 py-3 rounded hover:bg-blue-600 disabled:opacity-50"
        >
          {loading ? 'Procesando...' : 'Pagar $50.00'}
        </button>
      </form>
    </div>
  );
}
```

---

## 📋 PASO 3: Deploy en Producción

### 3.1 Deploy del MCP Server

**Opción A: Render.com (Gratis)**

```bash
# 1. Push a GitHub (ya lo hicimos)
git push origin main

# 2. Ir a render.com
# 3. New Web Service
# 4. Conectar repositorio: ecolonco/agentprovisionmcpserver
# 5. Configurar:
#    - Build Command: pip install -r requirements.txt
#    - Start Command: uvicorn src.api.main:app --host 0.0.0.0 --port 8000
# 6. Agregar variables de entorno (desde .env.example)
```

**Opción B: Railway.app**

```bash
# 1. Instalar Railway CLI
npm i -g @railway/cli

# 2. Login
railway login

# 3. Crear proyecto
railway init

# 4. Deploy
railway up
```

**Opción C: AWS con Terraform**

```bash
cd terraform/
terraform init
terraform apply
```

### 3.2 Configurar Variables en Vercel (TalleresIA)

```bash
# En Vercel Dashboard > tu-proyecto > Settings > Environment Variables

NEXT_PUBLIC_MCP_API_URL = https://mcp-server.onrender.com/api/v1
NEXT_PUBLIC_MCP_API_KEY = mcp_talleresia_production_key_xyz789
```

---

## 🔄 Flujo Completo en Acción

```
┌─────────────────────────────────────────────────────────────────┐
│                    FLUJO COMPLETO                                │
└─────────────────────────────────────────────────────────────────┘

1. Usuario en talleresia-frontend.vercel.app hace clic en "Comprar"
   │
   ▼
2. Frontend llama a MCP Server:
   POST https://mcp.tudominio.com/api/v1/payments/create-intent
   Headers:
     X-API-Key: mcp_talleresia_abc123
     X-Tenant: talleresia
   Body:
     { amount: 5000, customer_email: "alumno@example.com" }
   │
   ▼
3. MCP Server (automáticamente):
   ├─> Llama a Stripe API con credenciales de TalleresIA
   ├─> Crea Payment Intent
   ├─> Guarda en base de datos (audit log)
   └─> Devuelve client_secret
   │
   ▼
4. Frontend muestra Stripe Elements
   Usuario ingresa tarjeta
   Stripe procesa pago
   │
   ▼
5. Stripe envía webhook a MCP:
   POST https://mcp.tudominio.com/api/v1/payments/webhook
   Body: { type: "payment_intent.succeeded", ... }
   │
   ▼
6. MCP Server trigger workflow automático:
   ├─> ✅ Confirma pago en DB
   ├─> ✅ Activa acceso al taller
   ├─> ✅ Envía email de bienvenida (SendGrid)
   ├─> ✅ Agrega a Mailchimp
   ├─> ✅ Crea Zoom meeting
   ├─> ✅ Agrega a Google Calendar
   └─> ✅ Envía credenciales de acceso
   │
   ▼
7. Usuario recibe:
   ├─> Email de confirmación
   ├─> Link de Zoom
   ├─> Evento en calendario
   └─> Acceso a plataforma
```

---

## 🎓 Para Eunacom (Mismo MCP, Diferentes Credenciales)

```typescript
// En eunacomtest.cl, usas el MISMO código:

const mcpClient = new MCPClient(
  'https://mcp.tudominio.com/api/v1',
  'mcp_eunacom_def456',  // 👈 API Key diferente
  'eunacom'               // 👈 Tenant diferente
);

// ¡Y funciona igual!
await mcpClient.createPaymentIntent({...});
```

El MCP Server automáticamente:
- Usa las credenciales de Stripe de Eunacom
- Guarda los logs separados por tenant
- Aplica las reglas específicas de Eunacom

---

## 💡 Beneficios

### Sin MCP:
```typescript
// En TalleresIA:
await stripe.createPaymentIntent(...)      // 50 líneas
await sendEmail(...)                       // 30 líneas
await mailchimp.addSubscriber(...)         // 40 líneas
await zoom.createMeeting(...)              // 60 líneas
await calendar.createEvent(...)            // 50 líneas
// Total: ~230 líneas por proyecto

// Y duplicar TODO en Eunacom
```

### Con MCP:
```typescript
// En TalleresIA y Eunacom:
await mcpClient.createPaymentIntent(...)   // 1 llamada
// Total: ~10 líneas por proyecto
// El MCP se encarga de todo
```

---

## 🚀 Próximos Pasos

1. ✅ MCP Server funcionando (localhost o producción)
2. 📝 Configurar credenciales en `.env`
3. 🔌 Integrar en TalleresIA usando el código de arriba
4. 🧪 Probar con pagos de prueba de Stripe
5. 📧 Agregar más connectors (Mailchimp, Zoom, etc.)
6. 🎯 Replicar en Eunacom

---

¿Listo para empezar? ¡Pregúntame si necesitas ayuda con algún paso! 🎉
