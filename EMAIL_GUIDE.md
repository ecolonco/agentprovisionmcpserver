# 📧 Guía de Envío de Correos con Gmail

## Gmail SMTP en el MCP Server

**El MCP Server ahora incluye un sistema completo de envío de correos electrónicos usando Gmail SMTP**.

### ✨ Características

- ✅ **Multi-tenant** - Credenciales separadas por proyecto (TalleresIA, Eunacom, etc.)
- ✅ **Templates HTML** - Correos profesionales con diseño responsive
- ✅ **Async/Non-blocking** - No bloquea el servidor
- ✅ **Audit logs** - Registro completo de todos los envíos
- ✅ **Retry logic** - Reintentos automáticos en caso de fallo
- ✅ **Attachments** - Soporte para archivos adjuntos

---

## 🚀 Configuración Rápida

### **Paso 1: Generar App Password en Gmail**

Para usar Gmail SMTP necesitas un **App Password** (no tu contraseña normal):

1. Ve a tu cuenta de Gmail
2. Activa **Verificación en 2 pasos**: https://myaccount.google.com/security
3. Ve a **App Passwords**: https://myaccount.google.com/apppasswords
4. Selecciona "Correo" y "Otro (nombre personalizado)"
5. Ingresa "MCP Server TalleresIA"
6. Copia la contraseña de 16 caracteres (ej: `abcd efgh ijkl mnop`)

### **Paso 2: Configurar en MCP Server**

Edita `/Users/jorgeaguilera/Documents/GitHub/AgentprovisionMCPserver/.env`:

```bash
# Gmail SMTP para TalleresIA
GMAIL_SMTP_USER_TALLERESIA=tu_email@gmail.com
GMAIL_SMTP_PASSWORD_TALLERESIA=abcdefghijklmnop  # Los 16 caracteres SIN espacios
GMAIL_FROM_EMAIL_TALLERESIA=tu_email@gmail.com
GMAIL_FROM_NAME_TALLERESIA=TalleresIA
```

⚠️ **IMPORTANTE**:
- Usa el App Password de 16 caracteres, **NO tu contraseña de Gmail**
- Quita todos los espacios del App Password

### **Paso 3: Verificar Configuración**

Prueba que funciona:

```bash
curl -X GET https://mcp.tudominio.com/api/v1/emails/test \
  -H "X-API-Key: mcp_talleresia_abc123" \
  -H "X-Tenant: talleresia"
```

Respuesta esperada:
```json
{
  "status": "configured",
  "tenant": "talleresia",
  "smtp_host": "smtp.gmail.com",
  "smtp_port": 587,
  "from_email": "tu_email@gmail.com",
  "from_name": "TalleresIA",
  "smtp_user_configured": true,
  "smtp_password_configured": true
}
```

---

## 📬 Uso desde TalleresIA Frontend

### **Actualizar Cliente MCP**

Agrega estos métodos a `src/lib/mcp-client.ts`:

```typescript
// src/lib/mcp-client.ts

export interface SendEmailRequest {
  to_email: string;
  subject: string;
  html_content: string;
  text_content?: string;
  metadata?: Record<string, any>;
}

export interface SendTemplateEmailRequest {
  to_email: string;
  template_name: string;
  context: Record<string, any>;
  subject?: string;
}

export interface EmailResponse {
  status: string;
  message_id: string;
  to: string;
  subject: string;
  sent_at: string;
  tenant: string;
}

class MCPClient {
  // ... código existente ...

  /**
   * Enviar un correo personalizado
   */
  async sendEmail(request: SendEmailRequest): Promise<EmailResponse> {
    const response = await fetch(`${this.baseURL}/emails/send`, {
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
      throw new Error(error.detail || 'Error sending email');
    }

    return response.json();
  }

  /**
   * Enviar correo usando template
   */
  async sendTemplateEmail(request: SendTemplateEmailRequest): Promise<EmailResponse> {
    const response = await fetch(`${this.baseURL}/emails/send-template`, {
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
      throw new Error(error.detail || 'Error sending template email');
    }

    return response.json();
  }

  /**
   * Enviar confirmación de pago (shortcut)
   */
  async sendPaymentConfirmation(
    to_email: string,
    customer_name: string,
    amount: number,
    currency: string,
    description: string,
  ): Promise<EmailResponse> {
    const response = await fetch(`${this.baseURL}/emails/send-payment-confirmation`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': this.apiKey,
        'X-Tenant': this.tenant,
      },
      body: JSON.stringify({
        to_email,
        customer_name,
        amount,
        currency,
        description,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Error sending payment confirmation');
    }

    return response.json();
  }
}
```

---

## 💡 Ejemplos de Uso

### **Ejemplo 1: Enviar Correo Personalizado**

```typescript
// Después de un pago exitoso
async function handlePaymentSuccess() {
  try {
    await mcpClient.sendEmail({
      to_email: 'alumno@example.com',
      subject: '¡Bienvenido a TalleresIA!',
      html_content: `
        <h1>¡Gracias por inscribirte!</h1>
        <p>Tu pago ha sido confirmado.</p>
        <p>Accede a tu taller aquí: <a href="https://talleresia.cl/dashboard">Dashboard</a></p>
      `,
      text_content: 'Gracias por inscribirte! Accede a: https://talleresia.cl/dashboard',
    });

    console.log('Email enviado exitosamente');
  } catch (error) {
    console.error('Error enviando email:', error);
  }
}
```

### **Ejemplo 2: Usar Template de Confirmación de Pago**

```typescript
// Después de un pago con Stripe o Flow
async function sendPaymentEmail(paymentData) {
  try {
    const result = await mcpClient.sendTemplateEmail({
      to_email: paymentData.customer_email,
      template_name: 'payment_confirmation',
      context: {
        customer_name: paymentData.customer_name,
        amount: paymentData.amount.toLocaleString(),
        currency: 'CLP',
        description: paymentData.description,
        payment_date: new Date().toLocaleDateString('es-CL'),
        transaction_id: paymentData.payment_id,
        company_name: 'TalleresIA',
      },
    });

    console.log('Confirmación enviada:', result.message_id);
  } catch (error) {
    console.error('Error:', error);
  }
}
```

### **Ejemplo 3: Shortcut de Confirmación de Pago**

```typescript
// Forma más rápida
async function quickPaymentConfirmation() {
  await mcpClient.sendPaymentConfirmation(
    'alumno@example.com',
    'Juan Pérez',
    50000,
    'CLP',
    'Taller de IA Básico 2024'
  );
}
```

### **Ejemplo 4: Email de Suscripción Activada**

```typescript
async function sendSubscriptionEmail(subscriptionData) {
  await mcpClient.sendTemplateEmail({
    to_email: subscriptionData.email,
    template_name: 'subscription_activated',
    context: {
      customer_name: subscriptionData.customer_name,
      plan_name: subscriptionData.plan_name,
      amount: subscriptionData.amount.toLocaleString(),
      currency: 'CLP',
      activation_date: new Date().toLocaleDateString('es-CL'),
      next_billing_date: subscriptionData.next_billing_date,
      dashboard_url: 'https://talleresia.cl/dashboard',
      company_name: 'TalleresIA',
    },
  });
}
```

---

## 📧 Templates Disponibles

El MCP Server incluye templates pre-diseñados:

### 1. **payment_confirmation**

Variables requeridas:
```typescript
{
  customer_name: string;      // "Juan Pérez"
  amount: string;             // "50.000" (formateado)
  currency: string;           // "CLP"
  description: string;        // "Taller IA Básico"
  payment_date: string;       // "15 de Enero, 2024"
  transaction_id: string;     // "pay_123abc"
  company_name: string;       // "TalleresIA"
}
```

### 2. **subscription_activated**

Variables requeridas:
```typescript
{
  customer_name: string;      // "Juan Pérez"
  plan_name: string;          // "Plan Pro Mensual"
  amount: string;             // "10.000"
  currency: string;           // "CLP"
  activation_date: string;    // "15 de Enero, 2024"
  next_billing_date: string;  // "15 de Febrero, 2024"
  dashboard_url: string;      // "https://talleresia.cl/dashboard"
  company_name: string;       // "TalleresIA"
}
```

---

## 🎯 Integración Automática con Pagos

### **Auto-envío después de Pago Exitoso**

Modifica tu endpoint de pago para enviar email automáticamente:

```typescript
// src/app/api/checkout/route.ts o donde manejes pagos

async function handleSuccessfulPayment(paymentIntent) {
  // 1. Procesar pago
  // ...

  // 2. Enviar email de confirmación automáticamente
  await mcpClient.sendTemplateEmail({
    to_email: paymentIntent.customer_email,
    template_name: 'payment_confirmation',
    context: {
      customer_name: paymentIntent.customer_name,
      amount: (paymentIntent.amount / 100).toLocaleString(),
      currency: paymentIntent.currency.toUpperCase(),
      description: paymentIntent.description,
      payment_date: new Date().toLocaleDateString('es-CL'),
      transaction_id: paymentIntent.id,
      company_name: 'TalleresIA',
    },
  });

  // 3. Otros workflows (Zoom, Calendar, etc.)
  // ...
}
```

---

## 🔄 Flujo Completo: Pago + Email

```
┌──────────────────────────────────────────────────────────────┐
│         FLUJO: PAGO → EMAIL AUTOMÁTICO                        │
└──────────────────────────────────────────────────────────────┘

1. Usuario completa pago en TalleresIA
   │
   ▼
2. Frontend confirma pago exitoso
   │
   ▼
3. Frontend/Backend llama a MCP Server:
   POST https://mcp.tudominio.com/api/v1/emails/send-template
   Headers:
     X-API-Key: mcp_talleresia_abc123
     X-Tenant: talleresia
   Body:
     {
       "to_email": "alumno@example.com",
       "template_name": "payment_confirmation",
       "context": { ... }
     }
   │
   ▼
4. MCP Server:
   ├─> Obtiene credenciales Gmail de TalleresIA
   ├─> Renderiza template HTML con datos
   ├─> Se conecta a Gmail SMTP (TLS)
   ├─> Envía email
   ├─> Guarda audit log
   └─> Devuelve message_id
   │
   ▼
5. Gmail entrega el email al alumno ✅
   │
   ▼
6. Alumno recibe:
   - Email con diseño profesional
   - Confirmación de pago
   - Detalles de la transacción
   - Link al dashboard
```

---

## 🧪 Testing

### **Enviar Email de Prueba**

```bash
curl -X POST https://mcp.tudominio.com/api/v1/emails/send \
  -H "X-API-Key: mcp_talleresia_abc123" \
  -H "X-Tenant: talleresia" \
  -H "Content-Type: application/json" \
  -d '{
    "to_email": "tu_email@gmail.com",
    "subject": "🧪 Test desde MCP Server",
    "html_content": "<h1>¡Funciona!</h1><p>El sistema de correos está configurado correctamente.</p>"
  }'
```

### **Enviar Template de Prueba**

```bash
curl -X POST https://mcp.tudominio.com/api/v1/emails/send-payment-confirmation \
  -H "X-API-Key: mcp_talleresia_abc123" \
  -H "X-Tenant: talleresia" \
  -H "Content-Type: application/json" \
  -d '{
    "to_email": "tu_email@gmail.com",
    "customer_name": "Juan Prueba",
    "amount": 50000,
    "currency": "CLP",
    "description": "Test de Confirmación de Pago"
  }'
```

---

## ⚠️ Límites de Gmail

Gmail tiene límites de envío:

- **Cuentas gratuitas**: ~500 emails/día
- **Google Workspace**: ~2,000 emails/día

Para volúmenes mayores considera:
- Usar múltiples cuentas Gmail
- Migrar a SendGrid/Mailgun
- El código del MCP Server es fácil de adaptar

---

## 🎨 Personalizar Templates

### **Crear tu Propio Template**

1. Crea archivos en `src/templates/emails/`:

```bash
# HTML principal
src/templates/emails/bienvenida_taller.html

# Texto plano (fallback)
src/templates/emails/bienvenida_taller.txt

# Subject del email
src/templates/emails/bienvenida_taller.meta
```

2. En el HTML usa placeholders con `{{variable}}`:

```html
<!-- bienvenida_taller.html -->
<!DOCTYPE html>
<html>
<body>
  <h1>Hola {{student_name}}</h1>
  <p>Bienvenido al taller {{course_name}}</p>
  <p>Fecha de inicio: {{start_date}}</p>
  <a href="{{zoom_link}}">Unirse al Zoom</a>
</body>
</html>
```

3. Usa desde TalleresIA:

```typescript
await mcpClient.sendTemplateEmail({
  to_email: 'alumno@example.com',
  template_name: 'bienvenida_taller',
  context: {
    student_name: 'Juan',
    course_name: 'IA Básico',
    start_date: '20 de Enero',
    zoom_link: 'https://zoom.us/j/123456789',
  },
});
```

---

## 💡 Ventajas de Usar Gmail via MCP

✅ **Credenciales seguras** - No expuestas en frontend
✅ **Multi-tenant** - Un email por proyecto
✅ **Templates centralizados** - Actualiza en un solo lugar
✅ **Audit completo** - Historial de todos los envíos
✅ **Retry automático** - Reintentos si falla Gmail
✅ **Fácil debug** - Logs centralizados

---

## 📊 Ver Historial de Emails

Todos los envíos se guardan en audit logs:

```bash
# Ver últimos emails enviados
curl https://mcp.tudominio.com/api/v1/health/logs \
  -H "X-API-Key: mcp_talleresia_abc123" \
  | grep "email_sent"
```

---

## 🚀 Deploy en Producción

### **Configurar en Render.com**

En el dashboard de Render, agrega estas variables de entorno:

```
GMAIL_SMTP_USER_TALLERESIA=tu_email@gmail.com
GMAIL_SMTP_PASSWORD_TALLERESIA=abcdefghijklmnop
GMAIL_FROM_EMAIL_TALLERESIA=tu_email@gmail.com
GMAIL_FROM_NAME_TALLERESIA=TalleresIA
```

### **Verificar**

```bash
curl https://tu-mcp-server.onrender.com/api/v1/emails/test \
  -H "X-API-Key: your_production_key" \
  -H "X-Tenant: talleresia"
```

---

## ✅ Checklist de Implementación

- [ ] Activar 2FA en Gmail
- [ ] Generar App Password
- [ ] Configurar `.env` en MCP Server
- [ ] Probar endpoint `/emails/test`
- [ ] Enviar email de prueba
- [ ] Agregar código del cliente en TalleresIA
- [ ] Integrar con flujo de pagos
- [ ] Configurar variables en Render/Vercel
- [ ] Verificar en producción
- [ ] Personalizar templates si es necesario

---

¡El sistema de correos está listo para usar en TalleresIA! 📧✨
