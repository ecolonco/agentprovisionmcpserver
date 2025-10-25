# 🇨🇱 Guía de Integración Flow.cl para Chile

## Flow.cl en el MCP Server

**Flow.cl es el procesador de pagos líder en Chile**, ahora completamente integrado en el MCP Server.

### 💳 Medios de Pago Soportados

- **Webpay** → Tarjetas de crédito y débito chilenas
- **Servipag** → Pago en efectivo en puntos Servipag
- **Multicaja** → Recarga de saldo
- **Onepay** → Pago móvil
- **Transferencia bancaria**

---

## 🚀 Cómo Usar Flow.cl con TalleresIA

### **Paso 1: Obtener Credenciales de Flow.cl**

1. Regístrate en https://www.flow.cl
2. Crea una cuenta de comercio
3. Obtén tus credenciales:
   - **API Key**
   - **Secret Key**
4. Activa modo Sandbox para pruebas

### **Paso 2: Configurar en MCP Server**

Edita `/Users/jorgeaguilera/Documents/GitHub/AgentprovisionMCPserver/.env`:

```bash
# Flow.cl para TalleresIA
FLOW_API_KEY_TALLERESIA=tu_api_key_de_flow
FLOW_SECRET_KEY_TALLERESIA=tu_secret_key_de_flow
FLOW_SANDBOX_TALLERESIA=true  # false en producción
```

### **Paso 3: Usar desde TalleresIA Frontend**

Actualiza tu cliente MCP (`src/lib/mcp-client.ts`):

```typescript
// src/lib/mcp-client.ts

export interface FlowPaymentRequest {
  amount: number;  // En pesos chilenos (CLP)
  subject: string;
  customer_email: string;
  payment_method?: number;  // 1=Webpay, 2=Servipag, 3=Multicaja, 4=Todos
  url_return?: string;
  metadata?: Record<string, any>;
}

export interface FlowPaymentResponse {
  token: string;
  payment_url: string;
  flow_order?: number;
}

class MCPClient {
  // ... código existente ...

  /**
   * Crear un pago con Flow.cl (Chile)
   */
  async createFlowPayment(
    request: FlowPaymentRequest
  ): Promise<FlowPaymentResponse> {
    const response = await fetch(`${this.baseURL}/payments/flow/create`, {
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
      throw new Error(error.detail || 'Error creating Flow payment');
    }

    return response.json();
  }

  /**
   * Consultar estado de pago Flow
   */
  async getFlowPaymentStatus(token: string) {
    const response = await fetch(
      `${this.baseURL}/payments/flow/${token}`,
      {
        headers: {
          'X-API-Key': this.apiKey,
          'X-Tenant': this.tenant,
        },
      }
    );

    if (!response.ok) {
      throw new Error('Error fetching Flow payment status');
    }

    return response.json();
  }
}

export const mcpClient = new MCPClient(
  process.env.NEXT_PUBLIC_MCP_API_URL!,
  process.env.NEXT_PUBLIC_MCP_API_KEY!,
  'talleresia'
);
```

### **Paso 4: Implementar en tu Componente de Checkout**

```typescript
// src/app/checkout/page.tsx

'use client';

import { useState } from 'react';
import { mcpClient } from '@/lib/mcp-client';

export default function CheckoutPage() {
  const [loading, setLoading] = useState(false);

  async function handleFlowPayment(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);

    try {
      // 1. Crear orden de pago en Flow.cl vía MCP Server
      const flowPayment = await mcpClient.createFlowPayment({
        amount: 50000,  // $50.000 CLP
        subject: 'Taller de IA Básico 2024',
        customer_email: 'alumno@example.com',
        payment_method: 1,  // 1 = Webpay (tarjetas)
        url_return: 'https://talleresia.cl/payment-success',
        metadata: {
          taller_id: 'taller-ia-basico-2024',
          taller_name: 'IA Básico',
        },
      });

      console.log('Flow payment created:', flowPayment);

      // 2. Redirigir al usuario a la página de pago de Flow
      window.location.href = flowPayment.payment_url;

      // Flow redirigirá de vuelta a tu url_return después del pago

    } catch (err: any) {
      console.error('Error:', err);
      alert(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container mx-auto p-8">
      <h1 className="text-3xl font-bold mb-6">
        Checkout con Flow.cl 🇨🇱
      </h1>

      <div className="bg-white shadow-lg rounded-lg p-6 max-w-md">
        <h2 className="text-xl font-semibold mb-4">
          Taller de IA Básico 2024
        </h2>

        <div className="mb-4">
          <p className="text-gray-600">Precio:</p>
          <p className="text-3xl font-bold text-green-600">
            $50.000 CLP
          </p>
        </div>

        <div className="mb-6">
          <p className="text-sm text-gray-500">
            Métodos de pago aceptados:
          </p>
          <ul className="text-sm text-gray-600 mt-2">
            <li>✅ Webpay (tarjetas de crédito/débito)</li>
            <li>✅ Servipag (pago en efectivo)</li>
            <li>✅ Transferencia bancaria</li>
            <li>✅ Onepay (pago móvil)</li>
          </ul>
        </div>

        <button
          onClick={handleFlowPayment}
          disabled={loading}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition"
        >
          {loading ? 'Procesando...' : 'Pagar con Flow 💳'}
        </button>

        <p className="text-xs text-gray-500 mt-4 text-center">
          Powered by Flow.cl - Pago seguro
        </p>
      </div>
    </div>
  );
}
```

### **Paso 5: Manejar el Retorno del Pago**

```typescript
// src/app/payment-success/page.tsx

'use client';

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { mcpClient } from '@/lib/mcp-client';

export default function PaymentSuccessPage() {
  const searchParams = useSearchParams();
  const [paymentStatus, setPaymentStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = searchParams.get('token');

    if (token) {
      // Verificar estado del pago con MCP Server
      mcpClient.getFlowPaymentStatus(token)
        .then(status => {
          setPaymentStatus(status);
          setLoading(false);

          if (status.status === 'success') {
            // ¡Pago exitoso! Aquí puedes:
            // - Activar acceso al taller
            // - Enviar email de confirmación
            // - Actualizar base de datos
            // - etc.
          }
        })
        .catch(err => {
          console.error('Error checking payment:', err);
          setLoading(false);
        });
    }
  }, [searchParams]);

  if (loading) {
    return <div>Verificando pago...</div>;
  }

  if (paymentStatus?.status === 'success') {
    return (
      <div className="container mx-auto p-8">
        <div className="bg-green-100 border border-green-400 text-green-700 px-6 py-4 rounded-lg">
          <h1 className="text-2xl font-bold mb-2">¡Pago Exitoso! 🎉</h1>
          <p>Tu pago de ${paymentStatus.amount} CLP ha sido procesado.</p>
          <p className="text-sm mt-2">
            Orden: {paymentStatus.flow_order}
          </p>
          <p className="text-sm">
            Email: {paymentStatus.email}
          </p>
        </div>

        <div className="mt-6">
          <a
            href="/dashboard"
            className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700"
          >
            Ir a mis talleres
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-8">
      <div className="bg-red-100 border border-red-400 text-red-700 px-6 py-4 rounded-lg">
        <h1 className="text-2xl font-bold mb-2">Pago no completado</h1>
        <p>Hubo un problema con tu pago. Por favor, intenta nuevamente.</p>
      </div>
    </div>
  );
}
```

---

## 🔄 Flujo Completo con Flow.cl

```
┌──────────────────────────────────────────────────────────────┐
│                    FLUJO DE PAGO CON FLOW.CL                  │
└──────────────────────────────────────────────────────────────┘

1. Usuario en talleresia.cl hace clic en "Pagar con Flow"
   │
   ▼
2. Frontend llama a MCP Server:
   POST https://mcp.tudominio.com/api/v1/payments/flow/create
   Headers:
     X-API-Key: mcp_talleresia_abc123
     X-Tenant: talleresia
   Body:
     {
       amount: 50000,
       subject: "Taller IA Básico",
       customer_email: "alumno@example.com",
       payment_method: 1
     }
   │
   ▼
3. MCP Server:
   ├─> Obtiene credenciales de Flow para TalleresIA
   ├─> Genera firma HMAC-SHA256
   ├─> Llama a Flow API /payment/create
   ├─> Guarda audit log
   └─> Devuelve token y payment_url
   │
   ▼
4. Frontend redirige a Flow.cl:
   https://sandbox.flow.cl/app/web/pay.php?token=abc123...
   │
   ▼
5. Usuario completa pago en Flow.cl:
   ├─> Selecciona Webpay (tarjeta)
   ├─> Ingresa datos de tarjeta
   ├─> Flow procesa pago
   └─> Usuario es redirigido de vuelta
   │
   ▼
6. Flow envía webhook a MCP:
   POST https://mcp.tudominio.com/api/v1/payments/flow/webhook
   Params: { token: "abc123..." }
   │
   ▼
7. MCP Server procesa webhook:
   ├─> Valida firma de Flow
   ├─> Consulta estado del pago
   ├─> Guarda en base de datos
   ├─> Trigger workflow de activación
   └─> Envía confirmación por email
   │
   ▼
8. Usuario retorna a:
   https://talleresia.cl/payment-success?token=abc123
   │
   ▼
9. Frontend consulta estado:
   GET https://mcp.tudominio.com/api/v1/payments/flow/{token}
   │
   ▼
10. Muestra confirmación y activa acceso al taller ✅
```

---

## 💰 Métodos de Pago en Flow

```typescript
// Códigos de métodos de pago:

const FLOW_PAYMENT_METHODS = {
  WEBPAY: 1,          // Tarjetas de crédito/débito
  SERVIPAG: 2,        // Pago en efectivo
  MULTICAJA: 3,       // Recarga de saldo
  ALL_METHODS: 4,     // Todos los métodos
  ONEPAY: 9,          // Pago móvil
};

// Ejemplo: Solo tarjetas
await mcpClient.createFlowPayment({
  amount: 50000,
  subject: "Taller IA",
  customer_email: "alumno@example.com",
  payment_method: FLOW_PAYMENT_METHODS.WEBPAY  // Solo Webpay
});

// Ejemplo: Todos los métodos
await mcpClient.createFlowPayment({
  amount: 50000,
  subject: "Taller IA",
  customer_email: "alumno@example.com",
  payment_method: FLOW_PAYMENT_METHODS.ALL_METHODS  // Usuario elige
});
```

---

## 🧪 Testing con Sandbox

Flow.cl proporciona un entorno de pruebas:

```bash
# En .env (MCP Server)
FLOW_API_KEY_TALLERESIA=tu_sandbox_api_key
FLOW_SECRET_KEY_TALLERESIA=tu_sandbox_secret
FLOW_SANDBOX_TALLERESIA=true  # 👈 Importante!
```

**Tarjetas de prueba en Sandbox:**

| Tarjeta | Resultado |
|---------|-----------|
| 4051885600446623 | ✅ Aprobada |
| 5186059559590568 | ❌ Rechazada |

---

## 📊 Comparación: Stripe vs Flow.cl

| Feature | Stripe | Flow.cl |
|---------|--------|---------|
| **Mercado** | Internacional | Chile 🇨🇱 |
| **Moneda** | USD, EUR, etc. | CLP principalmente |
| **Tarjetas** | Todas | Webpay (chilenas) |
| **Efectivo** | ❌ No | ✅ Servipag |
| **Comisión** | ~2.9% + $0.30 | ~3.5% + IVA |
| **Integración** | Compleja | Simple |
| **MCP Support** | ✅ Sí | ✅ Sí |

---

## 🎯 Recomendación para tus Proyectos

### **TalleresIA (público chileno)**
```typescript
// Usar Flow.cl para pagos en CLP
await mcpClient.createFlowPayment({
  amount: 50000,  // $50.000 CLP
  payment_method: 4  // Todos los métodos
});
```

### **TalleresIA (público internacional)**
```typescript
// Usar Stripe para pagos en USD
await mcpClient.createPaymentIntent({
  amount: 5000,  // $50.00 USD
  currency: 'usd'
});
```

### **Eunacom (solo Chile)**
```typescript
// Solo Flow.cl
await mcpClient.createFlowPayment({
  amount: 80000,  // $80.000 CLP
  payment_method: 1  // Solo Webpay
});
```

---

## 🚀 Deploy en Producción

### 1. Obtener Credenciales de Producción

1. Ir a https://www.flow.cl
2. Completar verificación de comercio
3. Obtener credenciales de **producción**

### 2. Configurar en Render/Vercel

```bash
# En Render.com (MCP Server)
FLOW_API_KEY_TALLERESIA=tu_production_api_key
FLOW_SECRET_KEY_TALLERESIA=tu_production_secret
FLOW_SANDBOX_TALLERESIA=false  # 👈 Producción!
```

### 3. Configurar Webhook en Flow

En tu dashboard de Flow.cl:
- **URL de Confirmación**: `https://mcp.tudominio.com/api/v1/payments/flow/webhook`
- **URL de Retorno**: `https://talleresia.cl/payment-success`

---

## ✅ Checklist de Implementación

- [ ] Registrarse en Flow.cl
- [ ] Obtener API Key y Secret Key
- [ ] Configurar `.env` en MCP Server
- [ ] Agregar código del cliente en TalleresIA
- [ ] Probar en sandbox
- [ ] Configurar página de success
- [ ] Manejar webhooks
- [ ] Verificar en producción
- [ ] Configurar URLs en Flow dashboard

---

## 💡 Ventajas de Usar Flow vía MCP

✅ **Credenciales seguras** - No expuestas en frontend
✅ **Audit logs** - Historial completo de transacciones
✅ **Multi-tenant** - Misma integración para todos tus proyectos
✅ **Webhooks manejados** - Procesamiento automático
✅ **Retry logic** - Reintentos automáticos en fallos
✅ **Fácil mantenimiento** - Un solo lugar para actualizar

---

## 📚 Recursos

- **Flow API Docs**: https://www.flow.cl/docs/api.html
- **Dashboard Flow**: https://www.flow.cl/app
- **Soporte Flow**: soporte@flow.cl

---

¡Flow.cl está listo para usar en tu MCP Server! 🎉🇨🇱
