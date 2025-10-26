#!/bin/bash

# ============================================
# Setup Fork Script - MCP Server Aremko
# ============================================
# Este script configura tu repositorio local para trabajar con tu fork privado
#
# USO:
#   1. Primero crea el fork en GitHub (interfaz web)
#   2. Haz el fork privado en Settings
#   3. Ejecuta este script: bash setup_fork.sh
# ============================================

set -e  # Exit on error

echo ""
echo "🔧 MCP Server - Configuración de Fork Privado"
echo "=============================================="
echo ""

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Variables - EDITAR CON TUS DATOS
GITHUB_USERNAME="jorgeaguilera"  # ← CAMBIAR POR TU USUARIO
FORK_REPO_NAME="mcp-server-aremko"  # ← CAMBIAR SI USASTE OTRO NOMBRE

ORIGINAL_REPO="https://github.com/ecolonco/agentprovisionmcpserver.git"
FORK_REPO="https://github.com/${GITHUB_USERNAME}/${FORK_REPO_NAME}.git"

echo -e "${YELLOW}Configuración:${NC}"
echo "  Usuario GitHub: ${GITHUB_USERNAME}"
echo "  Repositorio fork: ${FORK_REPO_NAME}"
echo "  URL fork: ${FORK_REPO}"
echo ""

# Verificar que estamos en un repositorio git
if [ ! -d .git ]; then
    echo -e "${RED}❌ Error: No estás en un repositorio Git${NC}"
    echo "   Ejecuta este script desde: /Users/jorgeaguilera/Documents/GitHub/AgentprovisionMCPserver"
    exit 1
fi

echo -e "${GREEN}✅ Repositorio Git detectado${NC}"

# Verificar estado del repositorio
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${RED}❌ Error: Hay cambios sin commitear${NC}"
    echo "   Por favor commitea o descarta los cambios primero:"
    echo "   git status"
    exit 1
fi

echo -e "${GREEN}✅ Working tree limpio${NC}"

# Paso 1: Renombrar origin a upstream
echo ""
echo "📝 Paso 1: Renombrando 'origin' a 'upstream'..."
if git remote get-url upstream &> /dev/null; then
    echo -e "${YELLOW}⚠️  'upstream' ya existe, saltando...${NC}"
else
    git remote rename origin upstream
    echo -e "${GREEN}✅ Renombrado: origin → upstream${NC}"
fi

# Paso 2: Agregar tu fork como origin
echo ""
echo "📝 Paso 2: Agregando tu fork como 'origin'..."
if git remote get-url origin &> /dev/null; then
    echo -e "${YELLOW}⚠️  'origin' ya existe, actualizando URL...${NC}"
    git remote set-url origin "${FORK_REPO}"
else
    git remote add origin "${FORK_REPO}"
fi
echo -e "${GREEN}✅ Fork agregado como 'origin'${NC}"

# Paso 3: Verificar configuración
echo ""
echo "📝 Paso 3: Verificando configuración de remotes..."
echo ""
git remote -v
echo ""

# Paso 4: Configurar branch tracking
echo "📝 Paso 4: Configurando branch tracking..."
git branch --set-upstream-to=origin/main main
echo -e "${GREEN}✅ Branch tracking configurado${NC}"

# Paso 5: Push a tu fork
echo ""
echo "📝 Paso 5: Haciendo push a tu fork..."
echo -e "${YELLOW}⚠️  Esto subirá todos tus commits al fork privado${NC}"
read -p "¿Continuar? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    git push -u origin main
    echo -e "${GREEN}✅ Push completado exitosamente!${NC}"
else
    echo -e "${YELLOW}⚠️  Push cancelado. Puedes hacerlo manualmente con: git push -u origin main${NC}"
fi

# Resumen final
echo ""
echo "=============================================="
echo -e "${GREEN}🎉 ¡Configuración completada!${NC}"
echo "=============================================="
echo ""
echo "Tu repositorio ahora está configurado así:"
echo ""
echo "  📁 Repositorio local: $(pwd)"
echo "  🔄 origin (tu fork):  ${FORK_REPO}"
echo "  ⬆️  upstream (original): ${ORIGINAL_REPO}"
echo ""
echo "Comandos útiles:"
echo "  • Trabajar normalmente:        git add . && git commit -m 'msg' && git push"
echo "  • Recibir actualizaciones:     git fetch upstream && git merge upstream/main"
echo "  • Ver diferencias:             git diff upstream/main"
echo "  • Ver todos los remotes:       git remote -v"
echo ""
echo -e "${GREEN}✅ Tu código de Aremko ahora está en un repositorio privado!${NC}"
echo ""

# Crear archivo de referencia rápida
cat > FORK_WORKFLOW.md << 'HEREDOC'
# 🔄 Workflow con Fork Privado

## Configuración Actual

```bash
origin   → https://github.com/jorgeaguilera/mcp-server-aremko.git (TU FORK PRIVADO)
upstream → https://github.com/ecolonco/agentprovisionmcpserver.git (ORIGINAL)
```

## Trabajo Diario (Tu Fork)

```bash
# 1. Hacer cambios
vim src/integrations/aremko_db_connector.py

# 2. Commit
git add .
git commit -m "feat: mejora en conector Aremko"

# 3. Push a TU fork (privado)
git push origin main

# Todo va a TU repositorio, nadie más lo ve
```

## Recibir Actualizaciones del Original

```bash
# 1. Fetch cambios del repositorio original
git fetch upstream

# 2. Ver qué cambios hay
git log HEAD..upstream/main --oneline

# 3. Mergear cambios que te interesen
git merge upstream/main

# 4. Resolver conflictos si hay
# (Editar archivos con conflictos)
git add .
git commit -m "merge: actualizaciones desde upstream"

# 5. Push a tu fork
git push origin main
```

## Contribuir Mejoras al Original (Opcional)

```bash
# 1. Crear branch para feature
git checkout -b feature/mi-mejora

# 2. Hacer cambios
git add .
git commit -m "feat: nueva feature"

# 3. Push a TU fork
git push origin feature/mi-mejora

# 4. Crear Pull Request en GitHub
# Ir a: https://github.com/jorgeaguilera/mcp-server-aremko
# Click "Contribute" → "Open pull request"
# Seleccionar: jorgeaguilera:feature/mi-mejora → ecolonco:main
```

## Ventajas de Tu Fork Privado

✅ **Control Total**: Haces cambios sin afectar a nadie
✅ **Privacidad**: Tu código e implementación son privados
✅ **Flexibilidad**: Decides cuándo adoptar cambios del original
✅ **Reversibilidad**: Puedes deshacer cambios sin problema
✅ **Seguridad**: Tus credenciales nunca van al repo público

## Comandos Útiles

```bash
# Ver estado de remotes
git remote -v

# Ver diferencias con upstream
git diff upstream/main

# Ver commits que tienes que upstream no tiene
git log upstream/main..HEAD

# Ver commits que upstream tiene y tú no
git log HEAD..upstream/main

# Deshacer último commit (mantener cambios)
git reset --soft HEAD~1

# Ver branches
git branch -a
```

## Estructura Final

```
┌─────────────────────────────────────────────────┐
│   GitHub: ecolonco/agentprovisionmcpserver      │
│   (Repositorio público/compartido - ORIGINAL)   │
└─────────────────┬───────────────────────────────┘
                  │
                  │ git fetch upstream
                  │ git merge upstream/main
                  ▼
┌─────────────────────────────────────────────────┐
│   Local: /Users/jorgeaguilera/Documents/...    │
│   (Tu máquina)                                  │
└─────────────────┬───────────────────────────────┘
                  │
                  │ git push origin main
                  ▼
┌─────────────────────────────────────────────────┐
│   GitHub: jorgeaguilera/mcp-server-aremko      │
│   (Tu fork PRIVADO - solo tú lo ves)           │
└─────────────────────────────────────────────────┘
```

## Mantenimiento

- **Cada semana**: `git fetch upstream` para ver actualizaciones
- **Cada mes**: Revisar si hay mejoras útiles del upstream
- **Cada 3 meses**: Mergear actualizaciones importantes
- **Nunca**: No compartir este repositorio (es privado)

---

**¡Tu código de Aremko está seguro en tu fork privado!** 🔒✨
HEREDOC

echo -e "${GREEN}✅ Archivo de referencia creado: FORK_WORKFLOW.md${NC}"
echo ""
