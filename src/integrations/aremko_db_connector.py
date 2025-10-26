"""
Aremko Database Connector
Connects to Aremko's Django PostgreSQL database for current data
"""
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import asyncpg
from src.utils.logger import logger


class AremkoDBConnector:
    """
    Connector for Aremko's current PostgreSQL database
    Fetches data from Django models: Cliente, VentaReserva, Servicio, Producto, Pago
    """

    def __init__(self, tenant: str = "aremko"):
        """
        Initialize Aremko DB connector

        Args:
            tenant: Tenant identifier (default: aremko)
        """
        self.tenant = tenant

        # Get database connection from environment
        tenant_suffix = f"_{tenant.upper()}" if tenant != "aremko" else ""
        self.database_url = os.getenv(
            f"AREMKO_DATABASE_URL{tenant_suffix}",
            os.getenv("AREMKO_DATABASE_URL")
        )

        if not self.database_url:
            raise ValueError(f"AREMKO_DATABASE_URL not configured for tenant {tenant}")

        self.pool: Optional[asyncpg.Pool] = None
        logger.info(f"AremkoDBConnector initialized for tenant: {tenant}")

    async def connect(self):
        """Create database connection pool"""
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=10,
                timeout=30.0
            )
            logger.info("Connected to Aremko database")

    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Closed Aremko database connection")

    # ============================================
    # Cliente Methods
    # ============================================

    async def fetch_customers(
        self,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch customers from ventas_cliente table

        Args:
            limit: Maximum number of records
            offset: Pagination offset
            filters: Optional filters (e.g., {'telefono': '987654321'})

        Returns:
            List of customer dictionaries
        """
        await self.connect()

        query = """
            SELECT
                id,
                nombre,
                email,
                telefono,
                documento_identidad,
                pais,
                ciudad
            FROM ventas_cliente
            WHERE 1=1
        """
        params = []
        param_count = 1

        if filters:
            if 'telefono' in filters:
                query += f" AND telefono = ${param_count}"
                params.append(filters['telefono'])
                param_count += 1
            if 'email' in filters:
                query += f" AND email = ${param_count}"
                params.append(filters['email'])
                param_count += 1
            if 'documento_identidad' in filters:
                query += f" AND documento_identidad = ${param_count}"
                params.append(filters['documento_identidad'])
                param_count += 1

        query += f" ORDER BY id DESC LIMIT ${param_count} OFFSET ${param_count + 1}"
        params.extend([limit, offset])

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

            customers = []
            for row in rows:
                customers.append({
                    "id": row['id'],
                    "nombre": row['nombre'],
                    "email": row['email'],
                    "telefono": row['telefono'],
                    "documento_identidad": row['documento_identidad'],
                    "pais": row['pais'],
                    "ciudad": row['ciudad'],
                })

            logger.info(f"Fetched {len(customers)} customers from Aremko DB")
            return customers

    async def get_customer_by_id(self, customer_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific customer by ID"""
        await self.connect()

        query = """
            SELECT
                id, nombre, email, telefono,
                documento_identidad, pais, ciudad
            FROM ventas_cliente
            WHERE id = $1
        """

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, customer_id)

            if not row:
                return None

            return {
                "id": row['id'],
                "nombre": row['nombre'],
                "email": row['email'],
                "telefono": row['telefono'],
                "documento_identidad": row['documento_identidad'],
                "pais": row['pais'],
                "ciudad": row['ciudad'],
            }

    async def find_customer_by_identifier(
        self,
        identifier: str
    ) -> List[Dict[str, Any]]:
        """
        Find customer(s) by any identifier: name, phone, email, or RUT

        Args:
            identifier: Search term (phone, email, name, or RUT)

        Returns:
            List of matching customers
        """
        await self.connect()

        query = """
            SELECT
                id, nombre, email, telefono,
                documento_identidad, pais, ciudad
            FROM ventas_cliente
            WHERE
                telefono ILIKE $1
                OR email ILIKE $1
                OR nombre ILIKE $1
                OR documento_identidad = $2
            LIMIT 20
        """

        search_pattern = f"%{identifier}%"

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, search_pattern, identifier)

            customers = []
            for row in rows:
                customers.append({
                    "id": row['id'],
                    "nombre": row['nombre'],
                    "email": row['email'],
                    "telefono": row['telefono'],
                    "documento_identidad": row['documento_identidad'],
                    "pais": row['pais'],
                    "ciudad": row['ciudad'],
                })

            logger.info(f"Found {len(customers)} customers matching '{identifier}'")
            return customers

    # ============================================
    # VentaReserva Methods
    # ============================================

    async def fetch_customer_reservations(
        self,
        customer_id: int
    ) -> List[Dict[str, Any]]:
        """
        Fetch all reservations/sales for a specific customer

        Args:
            customer_id: Customer ID

        Returns:
            List of VentaReserva records
        """
        await self.connect()

        query = """
            SELECT
                id,
                cliente_id,
                fecha_creacion,
                fecha_reserva,
                total,
                pagado,
                saldo_pendiente,
                estado_pago,
                estado_reserva,
                codigo_giftcard,
                cobrado,
                comentarios
            FROM ventas_ventareserva
            WHERE cliente_id = $1
            ORDER BY fecha_creacion DESC
        """

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, customer_id)

            reservations = []
            for row in rows:
                reservations.append({
                    "id": row['id'],
                    "cliente_id": row['cliente_id'],
                    "fecha_creacion": row['fecha_creacion'],
                    "fecha_reserva": row['fecha_reserva'],
                    "total": float(row['total']) if row['total'] else 0.0,
                    "pagado": float(row['pagado']) if row['pagado'] else 0.0,
                    "saldo_pendiente": float(row['saldo_pendiente']) if row['saldo_pendiente'] else 0.0,
                    "estado_pago": row['estado_pago'],
                    "estado_reserva": row['estado_reserva'],
                    "codigo_giftcard": row['codigo_giftcard'],
                    "cobrado": row['cobrado'],
                    "comentarios": row['comentarios'],
                })

            logger.info(f"Fetched {len(reservations)} reservations for customer {customer_id}")
            return reservations

    async def fetch_reservation_services(
        self,
        reservation_id: int
    ) -> List[Dict[str, Any]]:
        """Fetch services for a specific reservation"""
        await self.connect()

        query = """
            SELECT
                rs.id,
                rs.servicio_id,
                rs.fecha_agendamiento,
                rs.cantidad_personas,
                s.nombre as servicio_nombre,
                s.precio_base as servicio_precio,
                s.tipo_servicio
            FROM ventas_reservaservicio rs
            JOIN ventas_servicio s ON rs.servicio_id = s.id
            WHERE rs.ventareserva_id = $1
        """

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, reservation_id)

            services = []
            for row in rows:
                services.append({
                    "id": row['id'],
                    "servicio_id": row['servicio_id'],
                    "servicio_nombre": row['servicio_nombre'],
                    "servicio_precio": float(row['servicio_precio']) if row['servicio_precio'] else 0.0,
                    "tipo_servicio": row['tipo_servicio'],
                    "fecha_agendamiento": row['fecha_agendamiento'],
                    "cantidad_personas": row['cantidad_personas'],
                })

            return services

    async def fetch_reservation_products(
        self,
        reservation_id: int
    ) -> List[Dict[str, Any]]:
        """Fetch products for a specific reservation"""
        await self.connect()

        query = """
            SELECT
                rp.id,
                rp.producto_id,
                rp.cantidad,
                p.nombre as producto_nombre,
                p.precio_base as producto_precio
            FROM ventas_reservaproducto rp
            JOIN ventas_producto p ON rp.producto_id = p.id
            WHERE rp.ventareserva_id = $1
        """

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, reservation_id)

            products = []
            for row in rows:
                products.append({
                    "id": row['id'],
                    "producto_id": row['producto_id'],
                    "producto_nombre": row['producto_nombre'],
                    "producto_precio": float(row['producto_precio']) if row['producto_precio'] else 0.0,
                    "cantidad": row['cantidad'],
                })

            return products

    async def fetch_customer_payments(
        self,
        customer_id: int
    ) -> List[Dict[str, Any]]:
        """
        Fetch all payments made by a customer

        Args:
            customer_id: Customer ID

        Returns:
            List of payment records
        """
        await self.connect()

        query = """
            SELECT
                p.id,
                p.venta_reserva_id,
                p.monto,
                p.metodo_pago,
                p.fecha_pago,
                vr.fecha_reserva
            FROM ventas_pago p
            JOIN ventas_ventareserva vr ON p.venta_reserva_id = vr.id
            WHERE vr.cliente_id = $1
            ORDER BY p.fecha_pago DESC
        """

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, customer_id)

            payments = []
            for row in rows:
                payments.append({
                    "id": row['id'],
                    "venta_reserva_id": row['venta_reserva_id'],
                    "monto": float(row['monto']) if row['monto'] else 0.0,
                    "metodo_pago": row['metodo_pago'],
                    "fecha_pago": row['fecha_pago'],
                    "fecha_reserva": row['fecha_reserva'],
                })

            logger.info(f"Fetched {len(payments)} payments for customer {customer_id}")
            return payments

    # ============================================
    # Analytics Queries
    # ============================================

    async def get_customer_stats(
        self,
        customer_id: int
    ) -> Dict[str, Any]:
        """
        Get comprehensive statistics for a customer

        Args:
            customer_id: Customer ID

        Returns:
            Dictionary with customer statistics
        """
        await self.connect()

        query = """
            SELECT
                COUNT(DISTINCT vr.id) as total_visitas,
                COALESCE(SUM(vr.total), 0) as total_gastado,
                COALESCE(AVG(vr.total), 0) as promedio_por_visita,
                MAX(vr.fecha_creacion) as ultima_visita,
                MIN(vr.fecha_creacion) as primera_visita,
                COUNT(DISTINCT CASE WHEN vr.fecha_creacion >= NOW() - INTERVAL '12 months'
                    THEN vr.id END) as visitas_ultimo_ano
            FROM ventas_ventareserva vr
            WHERE vr.cliente_id = $1
        """

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, customer_id)

            return {
                "customer_id": customer_id,
                "total_visitas": row['total_visitas'] or 0,
                "total_gastado": float(row['total_gastado']) if row['total_gastado'] else 0.0,
                "promedio_por_visita": float(row['promedio_por_visita']) if row['promedio_por_visita'] else 0.0,
                "ultima_visita": row['ultima_visita'],
                "primera_visita": row['primera_visita'],
                "visitas_ultimo_ano": row['visitas_ultimo_ano'] or 0,
            }

    async def get_customer_service_preferences(
        self,
        customer_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get service preferences for a customer (most frequently booked services)

        Args:
            customer_id: Customer ID

        Returns:
            List of services with booking counts
        """
        await self.connect()

        query = """
            SELECT
                s.id,
                s.nombre,
                s.tipo_servicio,
                COUNT(rs.id) as veces_reservado,
                MAX(rs.fecha_agendamiento) as ultima_reserva
            FROM ventas_reservaservicio rs
            JOIN ventas_servicio s ON rs.servicio_id = s.id
            JOIN ventas_ventareserva vr ON rs.ventareserva_id = vr.id
            WHERE vr.cliente_id = $1
            GROUP BY s.id, s.nombre, s.tipo_servicio
            ORDER BY veces_reservado DESC
            LIMIT 10
        """

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, customer_id)

            preferences = []
            for row in rows:
                preferences.append({
                    "servicio_id": row['id'],
                    "servicio_nombre": row['nombre'],
                    "tipo_servicio": row['tipo_servicio'],
                    "veces_reservado": row['veces_reservado'],
                    "ultima_reserva": row['ultima_reserva'],
                })

            return preferences

    async def get_inactive_customers(
        self,
        months: int = 12
    ) -> List[Dict[str, Any]]:
        """
        Get customers who haven't visited in the last N months

        Args:
            months: Number of months of inactivity

        Returns:
            List of inactive customers with their stats
        """
        await self.connect()

        query = """
            SELECT
                c.id,
                c.nombre,
                c.email,
                c.telefono,
                MAX(vr.fecha_creacion) as ultima_visita,
                COUNT(vr.id) as total_visitas_historicas,
                COALESCE(SUM(vr.total), 0) as total_gastado_historico
            FROM ventas_cliente c
            LEFT JOIN ventas_ventareserva vr ON c.id = vr.cliente_id
            GROUP BY c.id, c.nombre, c.email, c.telefono
            HAVING MAX(vr.fecha_creacion) < NOW() - INTERVAL '{} months'
               AND MAX(vr.fecha_creacion) IS NOT NULL
            ORDER BY total_gastado_historico DESC
            LIMIT 500
        """.format(months)

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query)

            customers = []
            for row in rows:
                customers.append({
                    "id": row['id'],
                    "nombre": row['nombre'],
                    "email": row['email'],
                    "telefono": row['telefono'],
                    "ultima_visita": row['ultima_visita'],
                    "total_visitas_historicas": row['total_visitas_historicas'] or 0,
                    "total_gastado_historico": float(row['total_gastado_historico']) if row['total_gastado_historico'] else 0.0,
                })

            logger.info(f"Found {len(customers)} inactive customers ({months}+ months)")
            return customers

    # ============================================
    # Services & Products
    # ============================================

    async def fetch_all_services(self) -> List[Dict[str, Any]]:
        """Fetch all available services"""
        await self.connect()

        query = """
            SELECT
                id,
                nombre,
                precio_base,
                duracion,
                tipo_servicio,
                activo,
                publicado_web,
                descripcion_web
            FROM ventas_servicio
            WHERE activo = true
            ORDER BY nombre
        """

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query)

            services = []
            for row in rows:
                services.append({
                    "id": row['id'],
                    "nombre": row['nombre'],
                    "precio_base": float(row['precio_base']) if row['precio_base'] else 0.0,
                    "duracion": row['duracion'],
                    "tipo_servicio": row['tipo_servicio'],
                    "activo": row['activo'],
                    "publicado_web": row['publicado_web'],
                    "descripcion_web": row['descripcion_web'],
                })

            return services

    async def fetch_all_products(self) -> List[Dict[str, Any]]:
        """Fetch all available products"""
        await self.connect()

        query = """
            SELECT
                id,
                nombre,
                precio_base,
                cantidad_disponible
            FROM ventas_producto
            ORDER BY nombre
        """

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query)

            products = []
            for row in rows:
                products.append({
                    "id": row['id'],
                    "nombre": row['nombre'],
                    "precio_base": float(row['precio_base']) if row['precio_base'] else 0.0,
                    "cantidad_disponible": row['cantidad_disponible'],
                })

            return products
