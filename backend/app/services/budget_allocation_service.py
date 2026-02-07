"""
Budget Allocation Service

Intelligently distributes user budget across trip components:
- Flights (30-40%)
- Hotels (25-35%)
- Food (15-20%)
- Activities (10-15%)
- Buffer (5-10%)

Adjusts allocation based on:
- Trip duration
- Number of travelers
- Travel style
- Destination type
"""
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class BudgetAllocationService:
    """Service to allocate trip budget across components"""
    
    # Base allocation percentages (mid-range travel style)
    BASE_ALLOCATION = {
        'flights': 0.35,      # 35%
        'hotels': 0.30,       # 30%
        'food': 0.18,         # 18%
        'activities': 0.12,   # 12%
        'buffer': 0.05        # 5%
    }
    
    def __init__(self):
        logger.info("BudgetAllocationService initialized")
    
    def allocate_budget(
        self,
        total_budget: float,
        currency: str,
        duration_days: int,
        travelers_count: int,
        travel_style: str = 'comfort',
        destination_type: str = 'city'
    ) -> Dict:
        """
        Allocate budget across trip components
        
        Args:
            total_budget: Total trip budget
            currency: Budget currency code
            duration_days: Trip duration in days
            travelers_count: Number of travelers
            travel_style: budget/comfort/luxury
            destination_type: beach/city/nature/adventure/culture
            
        Returns:
            Dict with budget allocation and per-component limits
        """
        try:
            logger.info(f"Allocating budget: {currency} {total_budget} for {duration_days} days, {travelers_count} travelers")
            
            # Start with base allocation
            allocation = self.BASE_ALLOCATION.copy()
            
            # Adjust based on trip duration
            allocation = self._adjust_for_duration(allocation, duration_days)
            
            # Adjust based on travel style
            allocation = self._adjust_for_style(allocation, travel_style)
            
            # Adjust based on destination type
            allocation = self._adjust_for_destination(allocation, destination_type)
            
            # Ensure percentages sum to 1.0
            total_pct = sum(allocation.values())
            if abs(total_pct - 1.0) > 0.01:
                logger.warning(f"Allocation percentages sum to {total_pct}, normalizing...")
                for key in allocation:
                    allocation[key] = allocation[key] / total_pct
            
            # Calculate absolute amounts
            budget_breakdown = {
                'total_budget': total_budget,
                'currency': currency,
                'allocation_percentages': allocation.copy(),
                'components': {
                    'flights': {
                        'allocated': round(total_budget * allocation['flights'], 2),
                        'percentage': round(allocation['flights'] * 100, 1),
                        'max_per_person': round((total_budget * allocation['flights']) / travelers_count, 2)
                    },
                    'hotels': {
                        'allocated': round(total_budget * allocation['hotels'], 2),
                        'percentage': round(allocation['hotels'] * 100, 1),
                        'max_per_night': round((total_budget * allocation['hotels']) / duration_days, 2),
                        'total_nights': duration_days
                    },
                    'food': {
                        'allocated': round(total_budget * allocation['food'], 2),
                        'percentage': round(allocation['food'] * 100, 1),
                        'per_person_per_day': round((total_budget * allocation['food']) / (duration_days * travelers_count), 2)
                    },
                    'activities': {
                        'allocated': round(total_budget * allocation['activities'], 2),
                        'percentage': round(allocation['activities'] * 100, 1),
                        'per_day': round((total_budget * allocation['activities']) / duration_days, 2)
                    },
                    'buffer': {
                        'allocated': round(total_budget * allocation['buffer'], 2),
                        'percentage': round(allocation['buffer'] * 100, 1)
                    }
                },
                'travelers_count': travelers_count,
                'duration_days': duration_days,
                'travel_style': travel_style,
                'destination_type': destination_type
            }
            
            logger.info(f"Budget allocated - Flights: {budget_breakdown['components']['flights']['allocated']}, "
                       f"Hotels: {budget_breakdown['components']['hotels']['allocated']}, "
                       f"Food: {budget_breakdown['components']['food']['allocated']}, "
                       f"Activities: {budget_breakdown['components']['activities']['allocated']}")
            
            return budget_breakdown
            
        except Exception as e:
            logger.error(f"Error allocating budget: {e}")
            # Return safe defaults
            return self._get_default_allocation(total_budget, currency, duration_days, travelers_count)
    
    def _adjust_for_duration(self, allocation: Dict, duration_days: int) -> Dict:
        """Adjust allocation based on trip duration"""
        
        if duration_days <= 3:
            # Short trips - flights are bigger portion
            allocation['flights'] += 0.05
            allocation['hotels'] -= 0.03
            allocation['activities'] -= 0.02
        elif duration_days >= 14:
            # Long trips - flights are smaller portion, hotels/food bigger
            allocation['flights'] -= 0.05
            allocation['hotels'] += 0.03
            allocation['food'] += 0.02
        
        return allocation
    
    def _adjust_for_style(self, allocation: Dict, style: str) -> Dict:
        """Adjust allocation based on travel style"""
        
        style = style.lower()
        
        if style == 'budget':
            # Budget travelers - maximize flights/hotels value, reduce activities
            allocation['flights'] += 0.03
            allocation['hotels'] += 0.02
            allocation['activities'] -= 0.03
            allocation['buffer'] -= 0.02
        elif style == 'luxury':
            # Luxury travelers - more on hotels/activities
            allocation['hotels'] += 0.05
            allocation['activities'] += 0.03
            allocation['flights'] -= 0.03
            allocation['food'] -= 0.02
            allocation['buffer'] -= 0.03
        
        return allocation
    
    def _adjust_for_destination(self, allocation: Dict, dest_type: str) -> Dict:
        """Adjust allocation based on destination type"""
        
        dest_type = dest_type.lower()
        
        if dest_type == 'beach':
            # Beach destinations - more on hotels (resorts), less on activities
            allocation['hotels'] += 0.05
            allocation['activities'] -= 0.05
        elif dest_type == 'adventure':
            # Adventure destinations - more on activities
            allocation['activities'] += 0.05
            allocation['hotels'] -= 0.03
            allocation['buffer'] -= 0.02
        elif dest_type == 'culture':
            # Cultural destinations - balanced activities and food
            allocation['activities'] += 0.03
            allocation['food'] += 0.02
            allocation['hotels'] -= 0.05
        
        return allocation
    
    def validate_budget_usage(
        self,
        budget_allocation: Dict,
        actual_costs: Dict,
        tolerance_percentage: float = 10.0
    ) -> Dict:
        """
        Validate actual costs against allocated budget
        
        Args:
            budget_allocation: Allocated budget from allocate_budget()
            actual_costs: Dict with actual costs per component
            tolerance_percentage: Acceptable variance (default 10%)
            
        Returns:
            Dict with validation results and disclaimers
        """
        try:
            total_budget = budget_allocation['total_budget']
            currency = budget_allocation['currency']
            components = budget_allocation['components']
            
            # Calculate total actual cost
            total_actual = sum(actual_costs.values())
            variance = total_actual - total_budget
            variance_pct = (variance / total_budget) * 100
            
            # Check per-component variance
            component_issues = []
            for component, actual_cost in actual_costs.items():
                if component not in components:
                    continue
                
                allocated = components[component]['allocated']
                comp_variance = actual_cost - allocated
                comp_variance_pct = (comp_variance / allocated) * 100 if allocated > 0 else 0
                
                if abs(comp_variance_pct) > tolerance_percentage:
                    component_issues.append({
                        'component': component.capitalize(),
                        'allocated': allocated,
                        'actual': actual_cost,
                        'variance': comp_variance,
                        'variance_pct': round(comp_variance_pct, 1),
                        'over_budget': comp_variance > 0
                    })
            
            # Build validation result
            is_within_budget = abs(variance_pct) <= tolerance_percentage
            
            result = {
                'is_within_budget': is_within_budget,
                'total_budget': total_budget,
                'total_actual': round(total_actual, 2),
                'variance': round(variance, 2),
                'variance_percentage': round(variance_pct, 1),
                'currency': currency,
                'tolerance_percentage': tolerance_percentage,
                'component_issues': component_issues,
                'has_disclaimer': not is_within_budget or len(component_issues) > 0
            }
            
            # Generate disclaimer if needed
            if result['has_disclaimer']:
                result['disclaimer'] = self._generate_budget_disclaimer(
                    variance_pct,
                    component_issues,
                    currency
                )
            
            logger.info(f"Budget validation - Within budget: {is_within_budget}, Variance: {variance_pct:.1f}%")
            
            return result
            
        except Exception as e:
            logger.error(f"Error validating budget: {e}")
            return {
                'is_within_budget': False,
                'has_disclaimer': True,
                'disclaimer': {
                    'severity': 'warning',
                    'message': 'Unable to validate budget. Please review costs carefully.',
                    'details': []
                }
            }
    
    def _generate_budget_disclaimer(
        self,
        variance_pct: float,
        component_issues: list,
        currency: str
    ) -> Dict:
        """Generate budget disclaimer with severity and details"""
        
        severity = 'info'
        if abs(variance_pct) > 20:
            severity = 'error'
        elif abs(variance_pct) > 10:
            severity = 'warning'
        
        if variance_pct > 0:
            # Over budget
            message = f"⚠️ Trip cost exceeds your budget by {abs(variance_pct):.1f}% ({currency} {abs(variance_pct * 100):.0f})"
            
            if component_issues:
                primary_issue = max(component_issues, key=lambda x: abs(x['variance']))
                reason = f"primarily due to higher {primary_issue['component'].lower()} costs"
            else:
                reason = "across multiple components"
            
            details = [
                f"Your estimated total is higher than planned {reason}.",
                "Consider the following options:"
            ]
            
            # Add specific recommendations
            for issue in sorted(component_issues, key=lambda x: abs(x['variance']), reverse=True)[:3]:
                comp_name = issue['component']
                if issue['over_budget']:
                    details.append(f"• {comp_name}: Look for more budget-friendly options (currently {abs(issue['variance_pct']):.0f}% over)")
            
            if severity == 'error':
                details.append("We strongly recommend adjusting your selections or increasing your budget.")
            
        else:
            # Under budget
            message = f"✓ Trip cost is {abs(variance_pct):.1f}% under budget"
            details = [
                f"You have {currency} {abs(variance_pct * 100):.0f} remaining in your budget.",
                "You could consider:"
            ]
            
            for issue in component_issues:
                if not issue['over_budget']:
                    comp_name = issue['component']
                    details.append(f"• Upgrading your {comp_name.lower()} options")
        
        return {
            'severity': severity,  # info/warning/error
            'message': message,
            'details': details,
            'component_breakdown': component_issues
        }
    
    def _get_default_allocation(
        self,
        total_budget: float,
        currency: str,
        duration_days: int,
        travelers_count: int
    ) -> Dict:
        """Return safe default allocation if calculation fails"""
        
        return {
            'total_budget': total_budget,
            'currency': currency,
            'components': {
                'flights': {'allocated': total_budget * 0.35, 'percentage': 35.0},
                'hotels': {'allocated': total_budget * 0.30, 'percentage': 30.0},
                'food': {'allocated': total_budget * 0.18, 'percentage': 18.0},
                'activities': {'allocated': total_budget * 0.12, 'percentage': 12.0},
                'buffer': {'allocated': total_budget * 0.05, 'percentage': 5.0}
            },
            'travelers_count': travelers_count,
            'duration_days': duration_days
        }
