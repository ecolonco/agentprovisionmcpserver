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

## 🔁 Suscripciones / Pagos Recurrentes

**¡NUEVA FUNCIONALIDAD!** El MCP Server ahora soporta suscripciones mensuales automáticas con Flow.cl.

### ¿Qué son las Suscripciones?

Las suscripciones permiten cobrar **automáticamente cada mes** a tus clientes sin que tengan que pagar manualmente. Perfecto para:

- **TalleresIA**: Membresía mensual con acceso a todos los talleres
- **Eunacom**: Acceso mensual a simulaciones y material de estudio
- **SaaS**: Cualquier servicio de suscripción mensual

### 📋 Paso 1: Configurar Planes en Flow.cl Dashboard

Antes de usar suscripciones, debes crear tus planes en Flow.cl:

1. Ingresa a https://www.flow.cl/app
2. Ve a **Suscripciones** → **Planes**
3. Crea un nuevo plan:
   - **ID del Plan**: `5000-mensual` (ejemplo)
   - **Nombre**: "Membresía Básica Mensual"
   - **Monto**: $5.000 CLP
   - **Periodicidad**: Mensual
   - **Auto-renovable**: Sí

Repite para cada plan que necesites (ej: `10000-mensual`, `20000-mensual`).

### 📋 Paso 2: Actualizar Cliente MCP con Suscripciones

```typescript
// src/lib/mcp-client.ts

export interface FlowSubscriptionRequest {
  amount: number;           // Monto mensual en CLP
  customer_email: string;   // Email del cliente
  plan_id: string;          // ID del plan en Flow (ej: "5000-mensual")
  url_return?: string;      // URL de retorno después del pago
  metadata?: Record<string, any>;
}

export interface FlowSubscriptionResponse {
  subscription_id: string;
  token: string;
  payment_url: string;
  customer_id: string;
  plan_id: string;
  status: string;
}

class MCPClient {
  // ... código existente ...

  /**
   * Crear una suscripción mensual con Flow.cl
   * Esta función crea el customer (si no existe) y la suscripción en un solo paso
   */
  async createFlowSubscription(
    request: FlowSubscriptionRequest
  ): Promise<FlowSubscriptionResponse> {
    const response = await fetch(
      `${this.baseURL}/payments/flow/subscription/create`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': this.apiKey,
          'X-Tenant': this.tenant,
        },
        body: JSON.stringify(request),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Error creating Flow subscription');
    }

    return response.json();
  }

  /**
   * Consultar estado de una suscripción
   */
  async getFlowSubscriptionStatus(subscriptionId: string) {
    const response = await fetch(
      `${this.baseURL}/payments/flow/subscription/${subscriptionId}/status`,
      {
        headers: {
          'X-API-Key': this.apiKey,
          'X-Tenant': this.tenant,
        },
      }
    );

    if (!response.ok) {
      throw new Error('Error fetching Flow subscription status');
    }

    return response.json();
  }

  /**
   * Cancelar una suscripción
   */
  async cancelFlowSubscription(subscriptionId: string) {
    const response = await fetch(
      `${this.baseURL}/payments/flow/subscription/${subscriptionId}/cancel`,
      {
        method: 'POST',
        headers: {
          'X-API-Key': this.apiKey,
          'X-Tenant': this.tenant,
        },
      }
    );

    if (!response.ok) {
      throw new Error('Error canceling Flow subscription');
    }

    return response.json();
  }
}
```

### 📋 Paso 3: Implementar Componente de Suscripción

```typescript
// src/app/subscribe/page.tsx

'use client';

import { useState } from 'react';
import { mcpClient } from '@/lib/mcp-client';

const SUBSCRIPTION_PLANS = [
  {
    id: '5000-mensual',
    name: 'Básico',
    price: 5000,
    description: 'Acceso a talleres básicos',
  },
  {
    id: '10000-mensual',
    name: 'Pro',
    price: 10000,
    description: 'Acceso a todos los talleres',
  },
  {
    id: '20000-mensual',
    name: 'Premium',
    price: 20000,
    description: 'Acceso VIP + mentoría',
  },
];

export default function SubscribePage() {
  const [loading, setLoading] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState(SUBSCRIPTION_PLANS[0]);
  const [email, setEmail] = useState('');

  async function handleSubscribe(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);

    try {
      // 1. Crear suscripción en Flow.cl vía MCP Server
      const subscription = await mcpClient.createFlowSubscription({
        amount: selectedPlan.price,
        customer_email: email,
        plan_id: selectedPlan.id,
        url_return: 'https://talleresia.cl/subscription-success',
        metadata: {
          plan_name: selectedPlan.name,
          plan_description: selectedPlan.description,
        },
      });

      console.log('Subscription created:', subscription);

      // 2. Redirigir al usuario a Flow para completar el primer pago
      window.location.href = subscription.payment_url;

      // 3. Después del primer pago exitoso:
      //    - Flow cobrará automáticamente cada mes
      //    - Recibirás webhooks en cada cobro
      //    - El usuario no necesita pagar manualmente

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
        Suscribirte a TalleresIA 🇨🇱
      </h1>

      <form onSubmit={handleSubscribe} className="max-w-2xl">
        {/* Email */}
        <div className="mb-6">
          <label className="block text-sm font-medium mb-2">
            Tu Email
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full px-4 py-2 border rounded-lg"
            placeholder="alumno@example.com"
          />
        </div>

        {/* Planes */}
        <div className="mb-6">
          <label className="block text-sm font-medium mb-2">
            Selecciona tu Plan
          </label>
          <div className="grid grid-cols-3 gap-4">
            {SUBSCRIPTION_PLANS.map((plan) => (
              <div
                key={plan.id}
                onClick={() => setSelectedPlan(plan)}
                className={`
                  p-4 border-2 rounded-lg cursor-pointer transition
                  ${selectedPlan.id === plan.id
                    ? 'border-blue-600 bg-blue-50'
                    : 'border-gray-300 hover:border-blue-400'
                  }
                `}
              >
                <h3 className="font-bold text-lg mb-1">{plan.name}</h3>
                <p className="text-2xl font-bold text-green-600 mb-2">
                  ${plan.price.toLocaleString()} CLP
                </p>
                <p className="text-sm text-gray-600">
                  {plan.description}
                </p>
                <p className="text-xs text-gray-500 mt-2">
                  Por mes, renovación automática
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Info */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <h4 className="font-semibold mb-2">📋 ¿Cómo funciona?</h4>
          <ul className="text-sm text-gray-700 space-y-1">
            <li>✅ Pagas el primer mes ahora con Webpay</li>
            <li>✅ Flow cobrará automáticamente cada mes</li>
            <li>✅ Puedes cancelar en cualquier momento</li>
            <li>✅ Sin compromiso de permanencia</li>
          </ul>
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={loading || !email}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition"
        >
          {loading ? 'Procesando...' : `Suscribirme por $${selectedPlan.price.toLocaleString()} CLP/mes`}
        </button>

        <p className="text-xs text-gray-500 mt-4 text-center">
          Powered by Flow.cl - Pago seguro con renovación automática
        </p>
      </form>
    </div>
  );
}
```

### 📋 Paso 4: Página de Gestión de Suscripciones

```typescript
// src/app/my-subscription/page.tsx

'use client';

import { useEffect, useState } from 'react';
import { mcpClient } from '@/lib/mcp-client';

export default function MySubscriptionPage() {
  const [subscription, setSubscription] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [canceling, setCanceling] = useState(false);

  useEffect(() => {
    loadSubscription();
  }, []);

  async function loadSubscription() {
    try {
      // Obtener subscriptionId de tu base de datos o localStorage
      const subscriptionId = localStorage.getItem('subscription_id');

      if (subscriptionId) {
        const status = await mcpClient.getFlowSubscriptionStatus(subscriptionId);
        setSubscription(status);
      }
    } catch (err) {
      console.error('Error loading subscription:', err);
    } finally {
      setLoading(false);
    }
  }

  async function handleCancel() {
    if (!confirm('¿Estás seguro de cancelar tu suscripción?')) {
      return;
    }

    setCanceling(true);
    try {
      await mcpClient.cancelFlowSubscription(subscription.subscription_id);
      alert('Suscripción cancelada exitosamente');
      loadSubscription(); // Recargar estado
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    } finally {
      setCanceling(false);
    }
  }

  if (loading) {
    return <div>Cargando...</div>;
  }

  if (!subscription) {
    return (
      <div className="container mx-auto p-8">
        <p>No tienes una suscripción activa.</p>
        <a href="/subscribe" className="text-blue-600 hover:underline">
          Suscribirte ahora
        </a>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-8">
      <h1 className="text-3xl font-bold mb-6">Mi Suscripción</h1>

      <div className="bg-white shadow-lg rounded-lg p-6 max-w-2xl">
        {/* Estado */}
        <div className="mb-4">
          <span className={`
            inline-block px-3 py-1 rounded-full text-sm font-semibold
            ${subscription.status === 'active'
              ? 'bg-green-100 text-green-800'
              : 'bg-red-100 text-red-800'
            }
          `}>
            {subscription.status === 'active' ? '✅ Activa' : '❌ Inactiva'}
          </span>
        </div>

        {/* Plan */}
        <div className="mb-4">
          <p className="text-gray-600 text-sm">Plan</p>
          <p className="text-2xl font-bold">{subscription.plan_id}</p>
        </div>

        {/* Monto */}
        <div className="mb-4">
          <p className="text-gray-600 text-sm">Monto mensual</p>
          <p className="text-2xl font-bold text-green-600">
            ${subscription.amount?.toLocaleString()} CLP
          </p>
        </div>

        {/* Email */}
        <div className="mb-4">
          <p className="text-gray-600 text-sm">Email</p>
          <p className="text-lg">{subscription.email}</p>
        </div>

        {/* Próximo cobro */}
        {subscription.next_payment_date && (
          <div className="mb-4">
            <p className="text-gray-600 text-sm">Próximo cobro</p>
            <p className="text-lg">
              {new Date(subscription.next_payment_date).toLocaleDateString('es-CL')}
            </p>
          </div>
        )}

        {/* Cancelar */}
        {subscription.status === 'active' && (
          <button
            onClick={handleCancel}
            disabled={canceling}
            className="w-full bg-red-600 hover:bg-red-700 text-white font-bold py-3 px-6 rounded-lg disabled:opacity-50 transition"
          >
            {canceling ? 'Cancelando...' : 'Cancelar Suscripción'}
          </button>
        )}
      </div>
    </div>
  );
}
```

### 🔄 Flujo Completo de Suscripción

```
┌──────────────────────────────────────────────────────────────┐
│              FLUJO DE SUSCRIPCIÓN CON FLOW.CL                 │
└──────────────────────────────────────────────────────────────┘

1. Usuario selecciona plan y hace clic en "Suscribirme"
   │
   ▼
2. Frontend llama a MCP Server:
   POST https://mcp.tudominio.com/api/v1/payments/flow/subscription/create
   Headers:
     X-API-Key: mcp_talleresia_abc123
     X-Tenant: talleresia
   Body:
     {
       amount: 10000,
       customer_email: "alumno@example.com",
       plan_id: "10000-mensual"
     }
   │
   ▼
3. MCP Server (automáticamente):
   ├─> Busca si el customer existe en Flow (por email)
   ├─> Si NO existe: crea customer en Flow
   ├─> Si SÍ existe: usa el customer_id existente
   ├─> Crea payment con subscription=1
   ├─> Genera firma HMAC-SHA256
   ├─> Llama a Flow API /payment/create
   ├─> Guarda audit log
   └─> Devuelve token, payment_url, subscription_id
   │
   ▼
4. Frontend redirige a Flow.cl:
   https://sandbox.flow.cl/app/web/pay.php?token=abc123...
   │
   ▼
5. Usuario completa PRIMER PAGO en Flow.cl:
   ├─> Selecciona Webpay (tarjeta)
   ├─> Ingresa datos de tarjeta
   ├─> Acepta términos de suscripción recurrente
   ├─> Flow procesa primer pago
   ├─> Flow guarda tarjeta para cobros futuros
   └─> Usuario es redirigido de vuelta
   │
   ▼
6. Flow envía webhook a MCP (primer pago):
   POST https://mcp.tudominio.com/api/v1/payments/flow/webhook
   Params: { token: "abc123..." }
   │
   ▼
7. MCP Server procesa webhook:
   ├─> Valida firma de Flow
   ├─> Confirma primer pago exitoso
   ├─> Activa suscripción
   ├─> Guarda en base de datos
   ├─> Envía email de bienvenida
   └─> Activa acceso del usuario
   │
   ▼
8. CADA MES (automático):
   Flow cobra automáticamente la tarjeta guardada
   │
   ▼
9. Flow envía webhook a MCP (cada mes):
   POST https://mcp.tudominio.com/api/v1/payments/flow/webhook
   Params: { token: "nuevo_token_mensual..." }
   │
   ▼
10. MCP Server procesa webhook mensual:
    ├─> Valida firma
    ├─> Confirma pago mensual
    ├─> Renueva acceso del usuario
    ├─> Envía email de confirmación
    └─> Guarda en historial de pagos

    ¡Usuario mantiene acceso sin hacer nada! ✅
```

### 💡 Ventajas de Suscripciones via MCP

✅ **Gestión automática de customers** - No necesitas manejar IDs de clientes
✅ **Un solo endpoint** - `createFlowSubscription()` lo hace todo
✅ **Webhooks automáticos** - Procesamiento de pagos mensuales sin intervención
✅ **Multi-tenant** - Cada proyecto con sus propios planes y credenciales
✅ **Audit completo** - Historial de todos los cobros mensuales
✅ **Cancelación simple** - Un endpoint para cancelar suscripciones

### ⚠️ Consideraciones Importantes

1. **Planes en Flow Dashboard**: Debes crear los planes ANTES en Flow.cl
2. **Plan IDs**: Los IDs deben coincidir exactamente (case-sensitive)
3. **Primer pago requerido**: El usuario DEBE completar el primer pago para activar la suscripción
4. **Webhooks críticos**: Asegúrate de configurar correctamente la URL de webhooks en Flow
5. **Cancelación**: Solo cancela la renovación automática, no reembolsa el mes actual

### 🧪 Testing de Suscripciones

```bash
# 1. Crear planes de prueba en Flow Sandbox
# 2. Usar tarjetas de prueba:
#    - 4051885600446623 (aprobada)
# 3. Monitorear webhooks con:
curl https://mcp.tudominio.com/api/v1/health/logs
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
