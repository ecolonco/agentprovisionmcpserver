# 🔒 Guía Completa: Crear Fork Privado del MCP Server

Esta guía te ayuda a crear tu propio fork privado del MCP Server para tener control total sobre tu implementación de Aremko.

---

## ⏱️ Tiempo Estimado: 10 minutos

---

## 📋 Pasos a Seguir

### **Paso 1: Crear Fork en GitHub (Interfaz Web)** ⏱️ 2 minutos

#### 1.1. Abrir el Repositorio Original

Abre en tu navegador:
```
https://github.com/ecolonco/agentprovisionmcpserver
```

#### 1.2. Hacer Fork

1. Click en el botón **"Fork"** (esquina superior derecha)

   ```
   ┌──────────────────────────────────────────────────┐
   │ ecolonco / agentprovisionmcpserver               │
   │                                       [Fork ▼]   │ ← AQUÍ
   └──────────────────────────────────────────────────┘
   ```

2. Configurar el fork:

   ```
   Owner: jorgeaguilera  (tu usuario de GitHub)

   Repository name: mcp-server-aremko
   (Puedes usar otro nombre si prefieres)

   Description: MCP Server - Aremko Private Implementation

   ☑ Copy the main branch only

   [Create fork]  ← CLICK
   ```

3. Esperar 10-30 segundos mientras se crea

#### 1.3. Hacer el Fork Privado (IMPORTANTE)

Una vez creado:

1. Ir a **Settings** del fork:
   ```
   https://github.com/jorgeaguilera/mcp-server-aremko/settings
   ```

2. Scroll hasta el final → Sección **"Danger Zone"**

3. Click en **"Change visibility"**

4. Seleccionar **"Make private"**

5. Confirmar escribiendo el nombre del repo: `mcp-server-aremko`

6. Click en **"I understand, make this repository private"**

✅ **Resultado**: Tu fork ahora es PRIVADO. Solo tú puedes verlo.

---

### **Paso 2: Configurar Tu Repositorio Local** ⏱️ 5 minutos

#### 2.1. Editar el Script de Setup

Abre el archivo `setup_fork.sh` y edita estas líneas:

```bash
# Variables - EDITAR CON TUS DATOS
GITHUB_USERNAME="jorgeaguilera"  # ← TU USUARIO de GitHub
FORK_REPO_NAME="mcp-server-aremko"  # ← El nombre que le pusiste al fork
```

Guarda el archivo.

#### 2.2. Ejecutar el Script

En la terminal:

```bash
cd /Users/jorgeaguilera/Documents/GitHub/AgentprovisionMCPserver

# Ejecutar script
bash setup_fork.sh
```

El script hará:
1. ✅ Renombrar `origin` → `upstream` (repo original)
2. ✅ Agregar tu fork como nuevo `origin`
3. ✅ Configurar branch tracking
4. ✅ Push de todos tus commits al fork privado
5. ✅ Crear archivo `FORK_WORKFLOW.md` con comandos útiles

#### 2.3. Verificar Configuración

```bash
# Ver remotes configurados
git remote -v

# Deberías ver:
# origin     https://github.com/jorgeaguilera/mcp-server-aremko.git (fetch)
# origin     https://github.com/jorgeaguilera/mcp-server-aremko.git (push)
# upstream   https://github.com/ecolonco/agentprovisionmcpserver.git (fetch)
# upstream   https://github.com/ecolonco/agentprovisionmcpserver.git (push)
```

✅ **Si ves esto, ¡está perfecto!**

---

### **Paso 3: Verificar que Todo Funciona** ⏱️ 2 minutos

#### 3.1. Hacer un Commit de Prueba

```bash
# Crear archivo de prueba
echo "# Mi implementación privada de Aremko" > AREMKO_PRIVATE_NOTES.md

# Commit
git add AREMKO_PRIVATE_NOTES.md
git commit -m "docs: notas privadas de implementación Aremko"

# Push a TU fork privado
git push origin main
```

#### 3.2. Verificar en GitHub

Abre tu fork:
```
https://github.com/jorgeaguilera/mcp-server-aremko
```

Deberías ver:
- ✅ Tu commit nuevo
- ✅ Todos los commits anteriores
- ✅ Un candado 🔒 indicando que es privado
- ✅ "This repository is private. Only you can see it."

---

## 🎯 ¿Qué Logramos?

```
ANTES:
┌─────────────────────────────────────────┐
│   ecolonco/agentprovisionmcpserver      │
│   (Repositorio compartido - PÚBLICO)    │
├─────────────────────────────────────────┤
│   ↑ Todos pushean aquí                  │
│   ↓ Todos reciben cambios de otros      │
│   ⚠️ Cambios de otros afectan tu código │
└─────────────────────────────────────────┘

DESPUÉS:
┌─────────────────────────────────────────┐
│   ecolonco/agentprovisionmcpserver      │
│   (Repositorio original)                │
└───────────┬─────────────────────────────┘
            │
            │ fetch (cuando TÚ quieras)
            ↓
┌─────────────────────────────────────────┐
│   TU MÁQUINA LOCAL                      │
│   /Users/jorgeaguilera/Documents/...    │
└───────────┬─────────────────────────────┘
            │
            │ push (siempre a tu fork)
            ↓
┌─────────────────────────────────────────┐
│   jorgeaguilera/mcp-server-aremko       │
│   (TU FORK PRIVADO) 🔒                  │
├─────────────────────────────────────────┤
│   ✅ Solo TÚ lo ves                     │
│   ✅ Control total                      │
│   ✅ Independiente del original         │
└─────────────────────────────────────────┘
```

---

## 📖 Workflow Diario

### Trabajo Normal (Tu Fork)

```bash
# 1. Hacer cambios en tu código
vim src/integrations/aremko_db_connector.py

# 2. Commit
git add .
git commit -m "feat(aremko): mejora en analytics"

# 3. Push a TU fork privado
git push origin main

# ✅ Solo va a TU repositorio, nadie más lo ve
```

### Recibir Actualizaciones del Original (Opcional)

Solo cuando TÚ quieras:

```bash
# 1. Ver si hay actualizaciones
git fetch upstream

# 2. Ver qué cambios hay
git log HEAD..upstream/main --oneline

# 3. Si te interesan, mergear
git merge upstream/main

# 4. Push a tu fork
git push origin main
```

---

## ✅ Checklist de Seguridad Post-Fork

- [ ] Fork creado en GitHub
- [ ] Fork configurado como PRIVADO (🔒)
- [ ] Remotes configurados correctamente (`git remote -v`)
- [ ] Push de prueba exitoso
- [ ] Archivo `.env` en `.gitignore` (ya está)
- [ ] NUNCA commitear credenciales:
  ```bash
  # Verificar antes de cada commit
  git status
  git diff

  # Si ves AREMKO_DATABASE_URL o SECRET_KEY → NO COMMITEAR
  ```

---

## 🚨 Qué NUNCA Hacer

❌ **Nunca:**
```bash
# NO subir archivo .env
git add .env  # ❌ NUNCA

# NO subir credenciales hardcodeadas
vim src/config.py
PASSWORD = "mi_password_real"  # ❌ NUNCA

# NO hacer el fork público
# En GitHub Settings → "Change visibility" → "Make public"  # ❌ NUNCA
```

✅ **Siempre:**
```bash
# Usar variables de entorno
.env  # ← en .gitignore
.env.example  # ← SIN credenciales reales

# Verificar antes de push
git status
git diff

# Mantener fork privado
```

---

## 🆘 Troubleshooting

### Problema: "remote origin already exists"

**Solución:**
```bash
# Eliminar origin actual
git remote remove origin

# Volver a ejecutar script
bash setup_fork.sh
```

### Problema: "Permission denied (publickey)"

**Solución:**
```bash
# Usar HTTPS en lugar de SSH
git remote set-url origin https://github.com/jorgeaguilera/mcp-server-aremko.git
```

### Problema: "Push rejected, non-fast-forward"

**Solución:**
```bash
# Fetch primero
git fetch origin

# Ver diferencias
git log HEAD..origin/main

# Mergear
git merge origin/main

# Ahora push
git push origin main
```

---

## 📚 Recursos

- **Workflow diario**: Ver `FORK_WORKFLOW.md` (creado por el script)
- **Integración Aremko**: Ver `AREMKO_INTEGRATION.md`
- **Variables de entorno**: Ver `.env.example`

---

## ✅ Confirmación Final

Si todo está bien, deberías poder responder SÍ a esto:

- [ ] ¿Ves tu fork en GitHub como privado (🔒)?
- [ ] ¿`git remote -v` muestra origin apuntando a tu fork?
- [ ] ¿Puedes hacer `git push origin main` sin errores?
- [ ] ¿Tu archivo `.env` NO está en GitHub?
- [ ] ¿Entiendes cómo recibir actualizaciones del upstream?

**Si respondiste SÍ a todo → ¡Felicitaciones! Tu fork privado está listo.** 🎉

---

## 🚀 Próximos Pasos

Ahora que tienes tu fork privado seguro, puedes:

1. **Continuar desarrollando** sin preocuparte por otros usuarios
2. **Agregar credenciales reales** en tu `.env` local (nunca en git)
3. **Hacer cambios personalizados** específicos para Aremko
4. **Deployar a producción** desde tu fork privado

---

**¿Necesitas ayuda?** Revisa `FORK_WORKFLOW.md` para comandos útiles.
