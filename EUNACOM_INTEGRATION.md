# 🏥 Guía de Integración para Eunacom

## ¿Qué puede hacer eunacomtest.cl con el MCP Server?

El MCP Server te proporciona una **infraestructura completa** para manejar pagos, autenticación y más, todo desde un solo lugar centralizado.

---

## 🎯 Casos de Uso Específicos para Eunacom

### **1. 💳 Sistema de Pagos y Suscripciones**

**Problema que resuelve:**
- Estudiantes de medicina chilenos necesitan pagar por acceso a simulaciones
- Algunos pagan una vez, otros quieren suscripción mensual
- Necesitas procesar pagos con Flow.cl (tarjetas chilenas, Webpay, etc.)

**Solución con MCP:**

#### **A. Pago Único (Simulación completa)**
```typescript
// En eunacomtest.cl
import { mcpClient } from '@/lib/mcp-client';

// Estudiante compra acceso a simulación EUNACOM
async function comprarSimulacion() {
  const pago = await mcpClient.createFlowPayment({
    amount: 15000,  // $15.000 CLP
    subject: 'Simulación EUNACOM 2024',
    customer_email: 'estudiante@med.cl',
    payment_method: 1,  // Webpay
    url_return: 'https://eunacomtest.cl/payment-success',
    metadata: {
      tipo: 'simulacion_completa',
      simulacion_id: 'eunacom-2024-01',
    },
  });

  // Redirige al estudiante a Flow para pagar
  window.location.href = pago.payment_url;

  // Flow procesa el pago y redirige de vuelta
  // MCP recibe webhook y confirma el pago
}
```

#### **B. Suscripción Mensual (Acceso ilimitado)**
```typescript
// Estudiante se suscribe mensualmente
async function suscripcionMensual() {
  const suscripcion = await mcpClient.createFlowSubscription({
    amount: 8000,  // $8.000 CLP/mes
    customer_email: 'estudiante@med.cl',
    plan_id: 'eunacom-mensual',
    url_return: 'https://eunacomtest.cl/subscription-success',
    metadata: {
      tipo: 'acceso_ilimitado',
      beneficios: ['Todas las simulaciones', 'Estadísticas', 'Soporte'],
    },
  });

  // Flow cobra automáticamente cada mes
  // No necesitas hacer nada más
}
```

**Beneficios:**
- ✅ No expones credenciales de Flow en tu frontend
- ✅ Historial completo de pagos en MCP
- ✅ Webhooks manejados automáticamente
- ✅ Soporte para renovaciones automáticas

---

### **2. 🔐 Sistema de Autenticación de Estudiantes**

**Problema que resuelve:**
- Necesitas registrar estudiantes
- Verificar que sean estudiantes reales (email .cl o .edu)
- Permitir login con contraseña
- Recuperación de contraseña olvidada

**Solución con MCP:**

```typescript
// En eunacomtest.cl
import { authClient } from '@/lib/auth-client';

// Registro de estudiante
async function registrarEstudiante() {
  await authClient.register({
    email: 'estudiante@med.uchile.cl',
    password: 'Secure123',
    full_name: 'Juan Pérez',
    phone: '+56912345678',
  });
  // → Estudiante recibe email de verificación
  // → Debe verificar antes de poder acceder
}

// Login
async function loginEstudiante() {
  const { access_token, user } = await authClient.login({
    email: 'estudiante@med.uchile.cl',
    password: 'Secure123',
  });

  // Guardar token y usar en requests
  localStorage.setItem('token', access_token);

  // Ahora puedes acceder a simulaciones
  await fetch('https://eunacomtest.cl/api/simulaciones', {
    headers: {
      'Authorization': `Bearer ${access_token}`,
    },
  });
}

// Recuperar contraseña
async function olvidoPassword() {
  await authClient.forgotPassword('estudiante@med.uchile.cl');
  // → Estudiante recibe email con link para resetear
}
```

**Beneficios:**
- ✅ Email verification obligatoria
- ✅ Contraseñas seguras (hash bcrypt)
- ✅ JWT tokens para autenticación
- ✅ Sistema de recuperación de contraseña
- ✅ Multi-tenant (usuarios de Eunacom separados de TalleresIA)

---

### **3. 📧 Notificaciones por Email (Ya lo tienes implementado)**

**Ya tienes tu sistema de emails**, pero si quisieras usar el MCP para ciertos emails automáticos:

```typescript
// Opcional: Usar MCP para emails transaccionales
async function enviarConfirmacionPago() {
  await mcpClient.sendPaymentConfirmation(
    'estudiante@med.cl',
    'Juan Pérez',
    15000,
    'CLP',
    'Simulación EUNACOM 2024'
  );
}
```

**Nota:** Como mencionaste que ya tienes tu sistema de emails, **NO necesitas usar esta parte**. El MCP respeta tu implementación existente.

---

## 🔄 Flujo Completo para Eunacom

### **Escenario 1: Estudiante compra simulación**

```
┌──────────────────────────────────────────────────────────────┐
│      FLUJO: ESTUDIANTE COMPRA SIMULACIÓN EUNACOM             │
└──────────────────────────────────────────────────────────────┘

1. Estudiante visita eunacomtest.cl
   │
   ▼
2. Se registra (si no tiene cuenta)
   eunacomtest.cl → MCP /auth/register
   → Recibe email de verificación
   → Verifica email
   │
   ▼
3. Hace login
   eunacomtest.cl → MCP /auth/login
   → Recibe JWT token
   │
   ▼
4. Selecciona simulación y hace clic en "Comprar"
   eunacomtest.cl → MCP /payments/flow/create
   Body: { amount: 15000, subject: "Simulación EUNACOM" }
   │
   ▼
5. MCP procesa:
   ├─> Obtiene credenciales de Flow para Eunacom
   ├─> Genera firma HMAC
   ├─> Crea orden en Flow
   └─> Retorna payment_url
   │
   ▼
6. Estudiante es redirigido a Flow.cl
   → Paga con Webpay (tarjeta)
   → Flow procesa pago
   │
   ▼
7. Flow envía webhook a MCP
   → MCP confirma pago
   → MCP guarda en audit log
   │
   ▼
8. Estudiante retorna a eunacomtest.cl/payment-success
   → eunacomtest.cl consulta estado del pago
   → Activa acceso a la simulación ✅
```

---

### **Escenario 2: Estudiante se suscribe mensualmente**

```
┌──────────────────────────────────────────────────────────────┐
│         FLUJO: SUSCRIPCIÓN MENSUAL EUNACOM                    │
└──────────────────────────────────────────────────────────────┘

1. Estudiante selecciona "Suscripción Mensual"
   │
   ▼
2. eunacomtest.cl → MCP /payments/flow/subscription/create
   Body: {
     amount: 8000,
     plan_id: "eunacom-mensual",
     customer_email: "estudiante@med.cl"
   }
   │
   ▼
3. MCP automáticamente:
   ├─> Busca/crea customer en Flow
   ├─> Crea payment con subscription=1
   └─> Retorna payment_url
   │
   ▼
4. Estudiante paga PRIMER mes en Flow
   → Flow guarda tarjeta
   │
   ▼
5. CADA MES (automático):
   Flow cobra $8.000 CLP de la tarjeta guardada
   │
   ▼
6. Flow envía webhook a MCP cada mes
   → MCP renueva acceso del estudiante
   → Estudiante mantiene acceso sin hacer nada ✅
```

---

## 💡 Integraciones Recomendadas para Eunacom

### **Lo que DEBERÍAS usar:**

#### 1. **Flow.cl para Pagos** ✅ RECOMENDADO
- Estudiantes chilenos pagan con Webpay
- Suscripciones mensuales automáticas
- Comisiones competitivas en Chile

```typescript
// Configurar en .env del MCP Server
FLOW_API_KEY_EUNACOM=tu_flow_api_key
FLOW_SECRET_KEY_EUNACOM=tu_flow_secret_key
FLOW_SANDBOX_EUNACOM=false  // Producción
```

#### 2. **Sistema de Autenticación** ✅ RECOMENDADO
- Registro de estudiantes con verificación
- Login seguro con JWT
- Recuperación de contraseña

```typescript
// Usar en eunacomtest.cl
import { authClient } from '@/lib/auth-client';

authClient.register({ email, password, full_name });
authClient.login({ email, password });
```

### **Lo que NO necesitas usar:**

#### ❌ Gmail SMTP
**Motivo:** Ya tienes tu sistema de emails implementado
**Acción:** Seguir usando tu implementación actual

#### ❌ Stripe (opcional)
**Motivo:** Flow.cl es mejor para Chile
**Acción:** Solo usa Stripe si planeas tener estudiantes internacionales

---

## 📋 Configuración Paso a Paso para Eunacom

### **Paso 1: Configurar Credenciales Flow.cl**

Edita `.env` en el MCP Server:

```bash
# Flow.cl para Eunacom
FLOW_API_KEY_EUNACOM=tu_api_key_de_flow
FLOW_SECRET_KEY_EUNACOM=tu_secret_key_de_flow
FLOW_SANDBOX_EUNACOM=false  # true para pruebas
```

### **Paso 2: Crear Planes de Suscripción en Flow.cl**

1. Ingresa a https://www.flow.cl/app
2. Ve a **Suscripciones** → **Planes**
3. Crea planes:
   - **eunacom-mensual**: $8.000 CLP/mes
   - **eunacom-trimestral**: $20.000 CLP/trimestre (descuento)

### **Paso 3: Agregar Cliente MCP a eunacomtest.cl**

Copia el código de los guías:
- `FLOW_CHILE_GUIDE.md` - Cliente Flow.cl
- `AUTH_GUIDE.md` - Cliente de autenticación

### **Paso 4: Crear Páginas en eunacomtest.cl**

```
eunacomtest.cl/
├── /register          # Registro de estudiantes
├── /login             # Login
├── /checkout          # Comprar simulación
├── /subscribe         # Suscripción mensual
├── /payment-success   # Confirmación de pago
└── /mi-cuenta         # Gestionar suscripción
```

---

## 💰 Precios Sugeridos para Eunacom

Basado en tu mercado (estudiantes de medicina en Chile):

| Producto | Precio CLP | Descripción |
|----------|------------|-------------|
| **Simulación única** | $15.000 - $20.000 | Acceso a 1 simulación completa |
| **Paquete 3 simulaciones** | $35.000 - $40.000 | 3 simulaciones (descuento) |
| **Suscripción mensual** | $8.000 - $12.000 | Acceso ilimitado por 1 mes |
| **Suscripción trimestral** | $20.000 - $30.000 | 3 meses (ahorro 25%) |
| **Suscripción anual** | $60.000 - $80.000 | 12 meses (ahorro 40%) |

---

## 🎯 Casos de Uso Específicos

### **Caso 1: Estudiante de 5to año compra simulación**

```typescript
// eunacomtest.cl - Compra única
const estudiante = {
  email: 'juan.perez@med.uchile.cl',
  tipo: 'estudiante_5to',
  universidad: 'Universidad de Chile',
};

// 1. Registrarse
await authClient.register({
  email: estudiante.email,
  password: 'MiPassword123',
  full_name: 'Juan Pérez',
});

// 2. Verificar email (click en link)
// 3. Login
const { access_token } = await authClient.login({
  email: estudiante.email,
  password: 'MiPassword123',
});

// 4. Comprar simulación
const pago = await mcpClient.createFlowPayment({
  amount: 15000,
  subject: 'Simulación EUNACOM - Medicina Interna',
  customer_email: estudiante.email,
  payment_method: 1,  // Webpay
});

// 5. Flow procesa pago → Estudiante obtiene acceso
```

### **Caso 2: Estudiante de 6to año se suscribe**

```typescript
// eunacomtest.cl - Suscripción mensual
const estudiante = {
  email: 'maria.lopez@med.udd.cl',
  tipo: 'estudiante_6to',
  preparando_eunacom: true,
};

// Crear suscripción mensual
const suscripcion = await mcpClient.createFlowSubscription({
  amount: 8000,  // $8.000/mes
  customer_email: estudiante.email,
  plan_id: 'eunacom-mensual',
  metadata: {
    tipo_estudiante: '6to_año',
    objetivo: 'preparacion_eunacom',
  },
});

// Flow cobra automáticamente cada mes
// Estudiante tiene acceso ilimitado mientras esté suscrito
```

### **Caso 3: Médico recién graduado - Pago único**

```typescript
// eunacomtest.cl - Médico recién graduado
const medico = {
  email: 'carlos.rodriguez@gmail.com',
  tipo: 'medico_recien_graduado',
};

// Compra paquete completo
const pago = await mcpClient.createFlowPayment({
  amount: 35000,  // Paquete de 3 simulaciones
  subject: 'Paquete Completo EUNACOM 2024',
  customer_email: medico.email,
  metadata: {
    paquete: 'completo',
    simulaciones: 3,
  },
});
```

---

## 📊 Dashboard de Administración

Podrías consultar el MCP para obtener estadísticas:

```typescript
// Consultar pagos recientes (futuro endpoint)
const pagos = await fetch('https://mcp.tudominio.com/api/v1/admin/payments', {
  headers: {
    'X-API-Key': 'admin_key_eunacom',
    'X-Tenant': 'eunacom',
  },
});

// Respuesta:
{
  total_revenue: 1500000,  // $1.5M CLP
  total_students: 120,
  active_subscriptions: 45,
  one_time_purchases: 75,
}
```

---

## 🔒 Seguridad Multi-Tenant

**Los datos de Eunacom están completamente separados de TalleresIA:**

- ✅ Usuarios de Eunacom ≠ Usuarios de TalleresIA
- ✅ Credenciales de Flow diferentes
- ✅ Audit logs separados
- ✅ Base de datos con tenant isolation

```sql
-- En la base de datos
SELECT * FROM users WHERE tenant = 'eunacom';  -- Solo usuarios de Eunacom
SELECT * FROM users WHERE tenant = 'talleresia';  -- Solo usuarios de TalleresIA
```

---

## ✅ Checklist de Implementación

### **Para empezar:**

- [ ] Obtener credenciales de Flow.cl
- [ ] Crear planes en Flow Dashboard
- [ ] Configurar `.env` en MCP Server
- [ ] Iniciar MCP Server (Docker o local)
- [ ] Copiar clientes a eunacomtest.cl
- [ ] Crear página de registro
- [ ] Crear página de login
- [ ] Crear página de checkout
- [ ] Crear página de suscripción
- [ ] Probar en sandbox Flow
- [ ] Configurar webhooks en Flow
- [ ] Deploy a producción

---

## 💡 Ventajas del MCP Server para Eunacom

### **Sin MCP:**
```typescript
// En eunacomtest.cl tendrías que:
- Implementar Flow.cl desde cero (firma HMAC, webhooks, etc.)
- Crear sistema de autenticación completo
- Manejar base de datos de usuarios
- Implementar recuperación de contraseña
- Configurar emails de verificación
- Manejar suscripciones manualmente
- TODO el código de integración
```

### **Con MCP:**
```typescript
// En eunacomtest.cl solo:
await mcpClient.createFlowSubscription({...});  // 1 línea
await authClient.register({...});  // 1 línea
```

✅ **Código reducido en ~90%**
✅ **Credenciales seguras** (no expuestas)
✅ **Audit completo** de todas las transacciones
✅ **Fácil mantenimiento** (actualizar en un solo lugar)
✅ **Multi-proyecto** (si tienes otros proyectos, mismo MCP)

---

## 🚀 Próximos Pasos

1. **Configura Flow.cl** - Obtén tus credenciales de producción
2. **Inicia el MCP Server** - Local o en Render.com
3. **Copia los clientes** - Código TypeScript listo para usar
4. **Prueba en sandbox** - Valida el flujo completo
5. **Deploy a producción** - ¡Empieza a recibir pagos!

---

## 📚 Recursos para Eunacom

- **FLOW_CHILE_GUIDE.md** - Guía completa de Flow.cl
- **AUTH_GUIDE.md** - Sistema de autenticación
- **INTEGRATION_GUIDE.md** - Integración general
- **API Docs** - http://localhost:8000/docs (cuando inicies MCP)

---

## 🎉 Resumen

**El MCP Server te da:**
1. ✅ Pagos con Flow.cl (una vez y suscripciones)
2. ✅ Autenticación completa de estudiantes
3. ✅ Backend seguro y escalable
4. ✅ Multi-tenant (separado de otros proyectos)
5. ✅ Audit logs completos
6. ✅ Código reutilizable

**Todo listo para eunacomtest.cl** 🏥✨
