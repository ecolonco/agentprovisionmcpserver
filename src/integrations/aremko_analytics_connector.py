"""
Aremko Analytics Connector
Customer behavior analysis, RFM scoring, and segmentation
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from src.integrations.aremko_db_connector import AremkoDBConnector
from src.integrations.aremko_legacy_connector import AremkoLegacyConnector
from src.utils.logger import logger


class AremkoAnalyticsConnector:
    """
    Analytics connector for Aremko
    Provides RFM analysis, customer segmentation, and behavior insights
    """

    def __init__(self, tenant: str = "aremko"):
        """
        Initialize Aremko Analytics connector

        Args:
            tenant: Tenant identifier (default: aremko)
        """
        self.tenant = tenant
        self.db_connector = AremkoDBConnector(tenant=tenant)
        self.legacy_connector = AremkoLegacyConnector(tenant=tenant)
        logger.info(f"AremkoAnalyticsConnector initialized for tenant: {tenant}")

    # ============================================
    # RFM Analysis
    # ============================================

    def calculate_rfm_score(
        self,
        customer_stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate RFM (Recency, Frequency, Monetary) score for a customer

        RFM Scoring:
        - Recency: Days since last visit (lower is better)
        - Frequency: Total number of visits (higher is better)
        - Monetary: Total amount spent (higher is better)

        Each dimension scored 1-5 (5 is best)

        Args:
            customer_stats: Customer statistics from get_customer_stats()

        Returns:
            Dictionary with RFM scores and segment
        """
        # Recency Score (days since last visit)
        if customer_stats['ultima_visita']:
            days_since_last = (datetime.now() - customer_stats['ultima_visita']).days

            if days_since_last <= 30:
                recency_score = 5  # Very recent
            elif days_since_last <= 90:
                recency_score = 4  # Recent
            elif days_since_last <= 180:
                recency_score = 3  # Moderate
            elif days_since_last <= 365:
                recency_score = 2  # Old
            else:
                recency_score = 1  # Very old
        else:
            days_since_last = None
            recency_score = 0  # Never visited

        # Frequency Score (number of visits)
        total_visitas = customer_stats['total_visitas']

        if total_visitas >= 20:
            frequency_score = 5  # VIP
        elif total_visitas >= 10:
            frequency_score = 4  # Loyal
        elif total_visitas >= 5:
            frequency_score = 3  # Regular
        elif total_visitas >= 2:
            frequency_score = 2  # Occasional
        else:
            frequency_score = 1  # One-time

        # Monetary Score (total spent in CLP)
        total_gastado = customer_stats['total_gastado']

        if total_gastado >= 1000000:  # $1M CLP
            monetary_score = 5  # High spender
        elif total_gastado >= 500000:   # $500k CLP
            monetary_score = 4  # Good spender
        elif total_gastado >= 200000:   # $200k CLP
            monetary_score = 3  # Average spender
        elif total_gastado >= 50000:    # $50k CLP
            monetary_score = 2  # Low spender
        else:
            monetary_score = 1  # Very low spender

        # Combined RFM Score (weighted average)
        # Recency is most important for reactivation campaigns
        rfm_score = (recency_score * 0.4) + (frequency_score * 0.3) + (monetary_score * 0.3)

        # Segment classification
        segment = self._classify_segment(recency_score, frequency_score, monetary_score)

        return {
            "recency_score": recency_score,
            "frequency_score": frequency_score,
            "monetary_score": monetary_score,
            "rfm_combined_score": round(rfm_score, 2),
            "days_since_last_visit": days_since_last,
            "segment": segment,
        }

    def _classify_segment(
        self,
        recency: int,
        frequency: int,
        monetary: int
    ) -> str:
        """
        Classify customer into segment based on RFM scores

        Segments:
        - VIP: High RFM across the board
        - Champions: Recent, frequent, high spenders
        - Loyal: Frequent visitors, good spenders
        - Promising: Recent, good potential
        - At Risk: Was good, now inactive
        - Hibernating: Inactive for long time
        - Lost: Very inactive, low engagement
        - New: Recent, few visits

        Args:
            recency: Recency score (1-5)
            frequency: Frequency score (1-5)
            monetary: Monetary score (1-5)

        Returns:
            Segment name
        """
        # VIP: Top scores
        if recency >= 4 and frequency >= 4 and monetary >= 4:
            return "VIP"

        # Champions: Recent, frequent, high spenders
        if recency >= 4 and frequency >= 3 and monetary >= 3:
            return "Champions"

        # Loyal: Frequent and good spenders (even if not super recent)
        if frequency >= 4 and monetary >= 3:
            return "Loyal"

        # Promising: Recent visitors with potential
        if recency >= 4 and (frequency <= 2 or monetary <= 2):
            return "Promising"

        # At Risk: Was good, now becoming inactive
        if recency <= 2 and frequency >= 3 and monetary >= 3:
            return "At Risk"

        # Hibernating: Long time inactive
        if recency == 1 and frequency >= 2:
            return "Hibernating"

        # New: Recent, few visits
        if recency >= 4 and frequency <= 2:
            return "New"

        # Lost: Very inactive
        if recency <= 1:
            return "Lost"

        # Default
        return "Occasional"

    # ============================================
    # Customer 360 Profile
    # ============================================

    async def generate_customer_360_profile(
        self,
        customer_id: int,
        include_legacy: bool = True
    ) -> Dict[str, Any]:
        """
        Generate comprehensive 360° profile for a customer

        Combines data from:
        - Current database
        - Legacy data (if available)
        - RFM analysis
        - Service preferences
        - Recommendations

        Args:
            customer_id: Customer ID from current database
            include_legacy: Whether to include legacy data

        Returns:
            Complete customer profile
        """
        # 1. Fetch current customer data
        customer = await self.db_connector.get_customer_by_id(customer_id)

        if not customer:
            return {"error": "Customer not found", "customer_id": customer_id}

        # 2. Fetch customer statistics
        stats = await self.db_connector.get_customer_stats(customer_id)

        # 3. Calculate RFM scores
        rfm = self.calculate_rfm_score(stats)

        # 4. Fetch service preferences
        preferences = await self.db_connector.get_customer_service_preferences(customer_id)

        # 5. Fetch reservations history
        reservations = await self.db_connector.fetch_customer_reservations(customer_id)

        # 6. Fetch payments history
        payments = await self.db_connector.fetch_customer_payments(customer_id)

        # 7. Legacy data (if requested)
        legacy_data = None
        if include_legacy:
            # Try to find matching legacy record
            if customer.get('telefono'):
                legacy_matches = await self.legacy_connector.find_legacy_customer_by_identifier(
                    customer['telefono']
                )
                if legacy_matches:
                    legacy_data = legacy_matches[0]  # Take best match

        # 8. Build complete profile
        profile = {
            "customer_id": customer_id,
            "basic_info": customer,
            "statistics": stats,
            "rfm_analysis": rfm,
            "service_preferences": preferences,
            "recent_reservations": reservations[:10],  # Last 10
            "recent_payments": payments[:10],  # Last 10
            "legacy_data": legacy_data,
            "generated_at": datetime.now().isoformat(),
        }

        logger.info(f"Generated 360° profile for customer {customer_id} (segment: {rfm['segment']})")
        return profile

    # ============================================
    # Behavioral Insights
    # ============================================

    async def analyze_customer_behavior(
        self,
        customer_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze customer behavior patterns

        Args:
            customer_profile: Customer 360° profile

        Returns:
            Behavioral insights dictionary
        """
        stats = customer_profile.get('statistics', {})
        preferences = customer_profile.get('service_preferences', [])
        rfm = customer_profile.get('rfm_analysis', {})

        insights = {
            "customer_id": customer_profile['customer_id'],
            "segment": rfm.get('segment', 'Unknown'),
            "ltv": stats.get('total_gastado', 0),  # Lifetime Value
            "avg_ticket": stats.get('promedio_por_visita', 0),
            "visit_frequency": self._calculate_visit_frequency(stats),
            "preferred_services": [p['servicio_nombre'] for p in preferences[:3]],
            "preferred_service_types": self._get_preferred_service_types(preferences),
            "seasonality": self._analyze_seasonality(customer_profile.get('recent_reservations', [])),
            "payment_behavior": self._analyze_payment_behavior(customer_profile.get('recent_payments', [])),
            "churn_risk": self._calculate_churn_risk(rfm, stats),
            "upsell_potential": self._calculate_upsell_potential(stats, preferences),
        }

        return insights

    def _calculate_visit_frequency(self, stats: Dict[str, Any]) -> str:
        """Calculate visit frequency description"""
        total_visitas = stats.get('total_visitas', 0)
        primera_visita = stats.get('primera_visita')
        ultima_visita = stats.get('ultima_visita')

        if not primera_visita or not ultima_visita:
            return "Unknown"

        months_active = ((ultima_visita - primera_visita).days / 30)
        if months_active < 1:
            months_active = 1

        visits_per_month = total_visitas / months_active

        if visits_per_month >= 2:
            return "Muy frecuente (2+ veces/mes)"
        elif visits_per_month >= 1:
            return "Frecuente (1 vez/mes)"
        elif visits_per_month >= 0.5:
            return "Regular (cada 2 meses)"
        elif visits_per_month >= 0.25:
            return "Ocasional (cada 4 meses)"
        else:
            return "Esporádico (< 1 vez/trimestre)"

    def _get_preferred_service_types(
        self,
        preferences: List[Dict[str, Any]]
    ) -> List[str]:
        """Get most preferred service types"""
        type_counts = {}

        for pref in preferences:
            tipo = pref.get('tipo_servicio', 'otro')
            count = pref.get('veces_reservado', 0)
            type_counts[tipo] = type_counts.get(tipo, 0) + count

        sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)
        return [t[0] for t in sorted_types[:3]]

    def _analyze_seasonality(
        self,
        reservations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze seasonal patterns in reservations"""
        if not reservations:
            return {"pattern": "unknown", "best_months": []}

        # Count by month
        month_counts = {}
        for res in reservations:
            fecha = res.get('fecha_creacion') or res.get('fecha_reserva')
            if fecha:
                month = fecha.month
                month_counts[month] = month_counts.get(month, 0) + 1

        if not month_counts:
            return {"pattern": "unknown", "best_months": []}

        sorted_months = sorted(month_counts.items(), key=lambda x: x[1], reverse=True)
        top_months = [m[0] for m in sorted_months[:3]]

        # Determine pattern
        month_names = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }

        summer_months = {1, 2, 12}  # Chilean summer
        winter_months = {6, 7, 8}   # Chilean winter

        summer_visits = sum(month_counts.get(m, 0) for m in summer_months)
        winter_visits = sum(month_counts.get(m, 0) for m in winter_months)

        if summer_visits > winter_visits * 1.5:
            pattern = "Prefiere verano"
        elif winter_visits > summer_visits * 1.5:
            pattern = "Prefiere invierno"
        else:
            pattern = "Sin preferencia estacional"

        return {
            "pattern": pattern,
            "best_months": [month_names[m] for m in top_months],
            "month_counts": {month_names[k]: v for k, v in month_counts.items()},
        }

    def _analyze_payment_behavior(
        self,
        payments: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze payment behavior"""
        if not payments:
            return {"preferred_method": "unknown", "payment_reliability": "unknown"}

        # Count payment methods
        method_counts = {}
        for payment in payments:
            method = payment.get('metodo_pago', 'unknown')
            method_counts[method] = method_counts.get(method, 0) + 1

        sorted_methods = sorted(method_counts.items(), key=lambda x: x[1], reverse=True)
        preferred_method = sorted_methods[0][0] if sorted_methods else "unknown"

        return {
            "preferred_method": preferred_method,
            "payment_methods_used": list(method_counts.keys()),
            "method_distribution": method_counts,
        }

    def _calculate_churn_risk(
        self,
        rfm: Dict[str, Any],
        stats: Dict[str, Any]
    ) -> str:
        """Calculate churn risk level"""
        recency = rfm.get('recency_score', 0)
        frequency = stats.get('visitas_ultimo_ano', 0)
        segment = rfm.get('segment', 'Unknown')

        # High risk segments
        if segment in ['At Risk', 'Hibernating', 'Lost']:
            return "Alto"

        # Low recency
        if recency <= 2:
            return "Medio-Alto"

        # No visits in last year
        if frequency == 0:
            return "Alto"

        # Active customers
        if recency >= 4 and frequency >= 2:
            return "Bajo"

        return "Medio"

    def _calculate_upsell_potential(
        self,
        stats: Dict[str, Any],
        preferences: List[Dict[str, Any]]
    ) -> str:
        """Calculate upsell/cross-sell potential"""
        avg_ticket = stats.get('promedio_por_visita', 0)
        total_visitas = stats.get('total_visitas', 0)
        service_variety = len(preferences)

        # High potential: frequent visitor, low variety
        if total_visitas >= 5 and service_variety <= 2:
            return "Alto (probar nuevos servicios)"

        # Medium potential: good spender, could spend more
        if avg_ticket >= 30000 and avg_ticket < 60000:
            return "Medio (aumentar ticket promedio)"

        # Low potential: already high spender, good variety
        if avg_ticket >= 60000 and service_variety >= 3:
            return "Bajo (ya es buen cliente)"

        return "Medio"

    # ============================================
    # Batch Analysis
    # ============================================

    async def batch_analyze_inactive_customers(
        self,
        months: int = 12,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Batch analyze inactive customers for reactivation campaigns

        Args:
            months: Months of inactivity
            limit: Maximum customers to analyze

        Returns:
            List of analyzed customer profiles
        """
        # Fetch inactive customers
        inactive = await self.db_connector.get_inactive_customers(months=months)

        results = []

        for customer in inactive[:limit]:
            # Generate profile
            profile = await self.generate_customer_360_profile(
                customer['id'],
                include_legacy=True
            )

            # Analyze behavior
            insights = await self.analyze_customer_behavior(profile)

            results.append({
                "profile": profile,
                "insights": insights,
                "reactivation_priority": self._calculate_reactivation_priority(
                    profile,
                    insights
                ),
            })

        # Sort by reactivation priority
        results.sort(key=lambda x: x['reactivation_priority'], reverse=True)

        logger.info(f"Analyzed {len(results)} inactive customers")
        return results

    def _calculate_reactivation_priority(
        self,
        profile: Dict[str, Any],
        insights: Dict[str, Any]
    ) -> int:
        """
        Calculate priority score for reactivation (0-100)

        Higher LTV and lower churn risk = higher priority
        """
        ltv = insights.get('ltv', 0)
        segment = insights.get('segment', 'Unknown')
        churn_risk = insights.get('churn_risk', 'Medio')

        score = 0

        # LTV contribution (0-50 points)
        if ltv >= 500000:
            score += 50
        elif ltv >= 200000:
            score += 40
        elif ltv >= 100000:
            score += 30
        elif ltv >= 50000:
            score += 20
        else:
            score += 10

        # Segment contribution (0-30 points)
        segment_scores = {
            "VIP": 30,
            "Champions": 28,
            "Loyal": 25,
            "At Risk": 22,
            "Hibernating": 15,
            "Lost": 10,
            "Occasional": 12,
        }
        score += segment_scores.get(segment, 10)

        # Churn risk (inverse - lower risk = higher priority for reactivation)
        # (0-20 points)
        if churn_risk == "Bajo":
            score += 20  # Easy to reactivate
        elif churn_risk == "Medio":
            score += 15
        elif churn_risk == "Medio-Alto":
            score += 10
        else:
            score += 5

        return min(score, 100)
