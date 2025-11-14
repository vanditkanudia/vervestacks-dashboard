"""
Enhanced LCOE Calculator with Financing and Life Assumptions
Implements industry-standard LCOE calculations with comprehensive financial modeling
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional

class EnhancedLCOECalculator:
    """
    Comprehensive LCOE calculator that includes:
    - Asset life and depreciation
    - Financing assumptions (debt/equity, interest rates)
    - Tax considerations
    - O&M costs (fixed and variable)
    - Degradation over asset life
    - Inflation adjustments
    - Multiple discount rate options
    """
    
    def __init__(self):
        # Default technology parameters based on 2024+ industry standards
        self.tech_params = {
            'solar': {
                'capex_per_kw': 800,           # $/kW (2024 values, utility-scale)
                'fixed_om_per_kw_year': 18,    # $/kW/year (includes inverter replacement)
                'variable_om_per_mwh': 0,      # $/MWh
                'asset_life_years': 25,        # Economic life
                'degradation_rate': 0.005,     # 0.5% per year
                'construction_time_years': 1,   # Construction period
            },
            'wind': {
                'capex_per_kw': 1100,          # $/kW (2024 values, modern onshore turbines)
                'fixed_om_per_kw_year': 28,    # $/kW/year (modern turbines, better reliability)
                'variable_om_per_mwh': 2,      # $/MWh (reduced with predictive maintenance)
                'asset_life_years': 25,        # Economic life (modern turbines last longer)
                'degradation_rate': 0.001,     # 0.1% per year (improved blade technology)
                'construction_time_years': 1.5, # Construction period (faster installation)
            },
            'hydro': {
                'capex_per_kw': 2500,          # $/kW
                'fixed_om_per_kw_year': 25,    # $/kW/year
                'variable_om_per_mwh': 2,      # $/MWh
                'asset_life_years': 50,        # Very long life
                'degradation_rate': 0.0,       # No degradation
                'construction_time_years': 4,   # Long construction
            },
            'nuclear': {
                'capex_per_kw': 6000,          # $/kW (high CAPEX)
                'fixed_om_per_kw_year': 100,   # $/kW/year
                'variable_om_per_mwh': 7,      # $/MWh
                'asset_life_years': 40,        # Long life
                'degradation_rate': 0.0,       # No degradation
                'construction_time_years': 6,   # Very long construction
            },
            'gas_ccgt': {
                'capex_per_kw': 1000,          # $/kW
                'fixed_om_per_kw_year': 20,    # $/kW/year
                'variable_om_per_mwh': 5,      # $/MWh (excluding fuel)
                'fuel_cost_per_mwh': 45,       # $/MWh (natural gas)
                'asset_life_years': 25,        # Economic life
                'degradation_rate': 0.001,     # 0.1% per year
                'construction_time_years': 3,   # Construction period
            }
        }
        
        # Default financial parameters
        self.financial_params = {
            'debt_fraction': 0.70,             # 70% debt financing
            'debt_interest_rate': 0.045,       # 4.5% nominal interest
            'debt_term_years': 20,             # Debt term
            'equity_return_rate': 0.12,        # 12% required equity return
            'tax_rate': 0.25,                  # 25% corporate tax rate
            'inflation_rate': 0.025,           # 2.5% inflation
            'depreciation_method': 'straight_line',  # or 'MACRS'
            'discount_rate': 0.08,             # WACC for NPV calculations
        }
        
        # Regional adjustments for different markets
        self.regional_adjustments = {
            'USA': {'risk_premium': 0.00, 'tax_rate': 0.21, 'wind_advantage': 1.0, 'solar_advantage': 1.0},
            'DEU': {'risk_premium': 0.005, 'tax_rate': 0.30, 'wind_advantage': 1.15, 'solar_advantage': 0.95}, # Better wind resources
            'CHN': {'risk_premium': 0.015, 'tax_rate': 0.25, 'wind_advantage': 1.1, 'solar_advantage': 1.0},
            'IND': {'risk_premium': 0.025, 'tax_rate': 0.25, 'wind_advantage': 1.0, 'solar_advantage': 1.1}, # Strong solar resources
            'BRA': {'risk_premium': 0.03, 'tax_rate': 0.34, 'wind_advantage': 1.2, 'solar_advantage': 1.0}, # Excellent wind resources
            'NOR': {'risk_premium': 0.002, 'tax_rate': 0.22, 'wind_advantage': 1.25, 'solar_advantage': 0.8}, # Excellent wind, poor solar
            'ITA': {'risk_premium': 0.008, 'tax_rate': 0.27, 'wind_advantage': 1.0, 'solar_advantage': 1.1}, # Good solar
            # Add more countries as needed
        }
        
        # Technology-specific adjustments based on capacity factor ranges
        self.technology_variants = {
            'wind': {
                'poor_wind': {'cf_threshold': 0.25, 'capex_multiplier': 1.2, 'om_multiplier': 1.1},  # Poor wind sites
                'average_wind': {'cf_threshold': 0.35, 'capex_multiplier': 1.0, 'om_multiplier': 1.0}, # Average sites
                'excellent_wind': {'cf_threshold': 0.45, 'capex_multiplier': 0.9, 'om_multiplier': 0.9}, # Excellent sites (economies of scale)
                'offshore_wind': {'cf_threshold': 0.50, 'capex_multiplier': 1.8, 'om_multiplier': 1.5}, # Offshore (higher CF, higher cost)
            },
            'solar': {
                'poor_solar': {'cf_threshold': 0.15, 'capex_multiplier': 1.1, 'om_multiplier': 1.1}, # Poor solar sites
                'average_solar': {'cf_threshold': 0.22, 'capex_multiplier': 1.0, 'om_multiplier': 1.0}, # Average sites
                'excellent_solar': {'cf_threshold': 0.30, 'capex_multiplier': 0.95, 'om_multiplier': 0.95}, # Excellent sites
            }
        }
        
        # Policy incentives by technology and region (realistic 2024+ policies)
        self.policy_incentives = {
            'USA': {
                'wind': {'ptc_per_mwh': 27, 'investment_tax_credit': 0.30},  # Production Tax Credit + ITC
                'solar': {'investment_tax_credit': 0.30, 'ptc_per_mwh': 0}   # Investment Tax Credit
            },
            'DEU': {
                'wind': {'feed_in_tariff': 20, 'investment_subsidy': 0.10},   # EUR/MWh premium
                'solar': {'feed_in_tariff': 15, 'investment_subsidy': 0.08}   # EUR/MWh premium
            },
            'BRA': {
                'wind': {'auction_premium': 15, 'tax_exemption': 0.15},       # Premium above market + tax benefits
                'solar': {'auction_premium': 10, 'tax_exemption': 0.10}
            },
            'ITA': {
                'wind': {'green_certificate': 20, 'investment_subsidy': 0.05},
                'solar': {'green_certificate': 25, 'investment_subsidy': 0.08}
            },
            'NOR': {
                'wind': {'green_certificate': 35, 'grid_connection_subsidy': 0.20}, # Strong wind support
                'solar': {'green_certificate': 15, 'grid_connection_subsidy': 0.10}  # Limited solar support
            }
        }
    
    def calculate_wacc(self, debt_fraction: float, debt_rate: float, 
                      equity_rate: float, tax_rate: float) -> float:
        """Calculate Weighted Average Cost of Capital (WACC)"""
        equity_fraction = 1 - debt_fraction
        after_tax_debt_cost = debt_rate * (1 - tax_rate)
        wacc = (debt_fraction * after_tax_debt_cost) + (equity_fraction * equity_rate)
        return wacc
    
    def calculate_debt_service(self, principal: float, interest_rate: float, 
                              term_years: int) -> float:
        """Calculate annual debt service payment"""
        if interest_rate == 0:
            return principal / term_years
        
        monthly_rate = interest_rate / 12
        num_payments = term_years * 12
        monthly_payment = principal * (monthly_rate * (1 + monthly_rate)**num_payments) / \
                         ((1 + monthly_rate)**num_payments - 1)
        return monthly_payment * 12
    
    def calculate_depreciation_schedule(self, capex: float, asset_life: int, 
                                      method: str = 'straight_line') -> np.ndarray:
        """Calculate depreciation schedule"""
        if method == 'straight_line':
            return np.full(asset_life, capex / asset_life)
        elif method == 'MACRS':
            # Simplified MACRS for renewable energy (5-year)
            macrs_rates = [0.20, 0.32, 0.192, 0.1152, 0.1152, 0.0576]
            schedule = np.zeros(asset_life)
            for i, rate in enumerate(macrs_rates[:min(len(macrs_rates), asset_life)]):
                schedule[i] = capex * rate
            return schedule
        else:
            raise ValueError(f"Unknown depreciation method: {method}")
    
    def calculate_generation_profile(self, capacity_factor: float, capacity_kw: float,
                                   degradation_rate: float, asset_life: int) -> np.ndarray:
        """Calculate annual generation with degradation"""
        base_generation = capacity_kw * capacity_factor * 8760 / 1000  # MWh
        generation_profile = np.zeros(asset_life)
        
        for year in range(asset_life):
            degradation_factor = (1 - degradation_rate) ** year
            generation_profile[year] = base_generation * degradation_factor
            
        return generation_profile
    
    def calculate_enhanced_lcoe(self, technology: str, capacity_factor: float, 
                               capacity_kw: float, iso_code: str = 'USA',
                               custom_params: Optional[Dict] = None) -> Dict:
        """
        Calculate comprehensive LCOE with full financial modeling
        
        Returns:
            Dictionary with LCOE breakdown and financial metrics
        """
        # Get technology parameters
        if technology not in self.tech_params:
            raise ValueError(f"Technology {technology} not supported")
        
        tech_params = self.tech_params[technology].copy()
        financial_params = self.financial_params.copy()
        
        # Apply custom parameters if provided
        if custom_params:
            tech_params.update(custom_params.get('tech_params', {}))
            financial_params.update(custom_params.get('financial_params', {}))
        
        # Apply regional adjustments
        if iso_code in self.regional_adjustments:
            regional = self.regional_adjustments[iso_code]
            financial_params['tax_rate'] = regional.get('tax_rate', financial_params['tax_rate'])
            # Adjust discount rate for country risk
            financial_params['discount_rate'] += regional.get('risk_premium', 0)
            
            # Apply regional technology advantages/disadvantages
            tech_advantage = regional.get(f'{technology}_advantage', 1.0)
            if tech_advantage != 1.0:
                # Adjust costs based on regional advantages (lower multiplier = better economics)
                cost_multiplier = 2.0 - tech_advantage  # 1.2 advantage becomes 0.8 cost multiplier
                tech_params['capex_per_kw'] *= cost_multiplier
                tech_params['fixed_om_per_kw_year'] *= cost_multiplier
        
        # Apply technology variant adjustments based on capacity factor
        if technology in self.technology_variants:
            variants = self.technology_variants[technology]
            selected_variant = 'average_' + technology  # default
            
            # Find the appropriate variant based on capacity factor
            for variant_name, variant_data in variants.items():
                if capacity_factor >= variant_data['cf_threshold']:
                    selected_variant = variant_name
            
            # Apply variant adjustments
            if selected_variant in variants:
                variant = variants[selected_variant]
                tech_params['capex_per_kw'] *= variant.get('capex_multiplier', 1.0)
                tech_params['fixed_om_per_kw_year'] *= variant.get('om_multiplier', 1.0)
                tech_params['variable_om_per_mwh'] *= variant.get('om_multiplier', 1.0)
        
        # Apply policy incentives
        policy_adjustments = {'capex_reduction': 0, 'revenue_benefit_per_mwh': 0}
        if iso_code in self.policy_incentives and technology in self.policy_incentives[iso_code]:
            incentives = self.policy_incentives[iso_code][technology]
            
            # Investment tax credits and subsidies reduce effective CAPEX
            itc = incentives.get('investment_tax_credit', 0)
            investment_subsidy = incentives.get('investment_subsidy', 0)
            grid_subsidy = incentives.get('grid_connection_subsidy', 0)
            policy_adjustments['capex_reduction'] = itc + investment_subsidy + grid_subsidy
            
            # Production incentives and feed-in tariffs provide revenue benefits
            ptc = incentives.get('ptc_per_mwh', 0)
            fit = incentives.get('feed_in_tariff', 0)
            premium = incentives.get('auction_premium', 0)
            green_cert = incentives.get('green_certificate', 0)
            policy_adjustments['revenue_benefit_per_mwh'] = ptc + fit + premium + green_cert
        
        # Calculate key metrics
        asset_life = tech_params['asset_life_years']
        base_capex = tech_params['capex_per_kw'] * capacity_kw
        # Apply policy incentive CAPEX reduction
        capex = base_capex * (1 - policy_adjustments['capex_reduction'])
        
        # WACC calculation
        wacc = self.calculate_wacc(
            financial_params['debt_fraction'],
            financial_params['debt_interest_rate'],
            financial_params['equity_return_rate'],
            financial_params['tax_rate']
        )
        
        # Generation profile with degradation
        generation_profile = self.calculate_generation_profile(
            capacity_factor, capacity_kw, 
            tech_params['degradation_rate'], asset_life
        )
        
        # Financial flows
        debt_amount = capex * financial_params['debt_fraction']
        annual_debt_service = self.calculate_debt_service(
            debt_amount, 
            financial_params['debt_interest_rate'],
            financial_params['debt_term_years']
        )
        
        # Annual costs
        fixed_om = tech_params['fixed_om_per_kw_year'] * capacity_kw
        
        # Calculate annual cash flows
        cash_flows = []
        cumulative_generation = 0
        
        for year in range(asset_life):
            # Revenue (not included in LCOE, but useful for analysis)
            generation_mwh = generation_profile[year]
            cumulative_generation += generation_mwh
            
            # Operating costs
            variable_om = tech_params['variable_om_per_mwh'] * generation_mwh
            fuel_cost = tech_params.get('fuel_cost_per_mwh', 0) * generation_mwh
            
            # Total O&M
            total_om = fixed_om + variable_om + fuel_cost
            
            # Inflation adjustment
            inflation_factor = (1 + financial_params['inflation_rate']) ** year
            total_om_real = total_om * inflation_factor
            
            # Depreciation (for tax shield)
            depreciation_schedule = self.calculate_depreciation_schedule(
                capex, asset_life, financial_params['depreciation_method']
            )
            depreciation = depreciation_schedule[year] if year < len(depreciation_schedule) else 0
            
            # Tax shield from depreciation
            tax_shield = depreciation * financial_params['tax_rate']
            
            # Policy revenue benefits (reduce effective costs)
            policy_revenue_benefit = policy_adjustments['revenue_benefit_per_mwh'] * generation_mwh * inflation_factor
            
            # Net cash flow (costs are negative)
            if year == 0:
                # Initial CAPEX
                cash_flow = -capex - total_om_real + tax_shield + policy_revenue_benefit
            else:
                # Operating years
                debt_payment = annual_debt_service if year < financial_params['debt_term_years'] else 0
                cash_flow = -total_om_real - debt_payment + tax_shield + policy_revenue_benefit
            
            cash_flows.append({
                'year': year,
                'generation_mwh': generation_mwh,
                'fixed_om': fixed_om * inflation_factor,
                'variable_om': variable_om * inflation_factor,
                'fuel_cost': fuel_cost * inflation_factor,
                'debt_service': annual_debt_service if year < financial_params['debt_term_years'] else 0,
                'depreciation': depreciation,
                'tax_shield': tax_shield,
                'net_cash_flow': cash_flow,
                'discount_factor': 1 / (1 + wacc) ** year
            })
        
        # Calculate NPV of costs and generation
        total_generation_pv = sum(cf['generation_mwh'] * cf['discount_factor'] for cf in cash_flows)
        total_costs_pv = sum(abs(cf['net_cash_flow']) * cf['discount_factor'] for cf in cash_flows)
        
        # LCOE calculation
        lcoe = total_costs_pv / total_generation_pv
        
        # Simple LCOE for comparison (your current method)
        simple_lcoe = tech_params['capex_per_kw'] / (capacity_factor * 8760)
        
        # Additional metrics
        total_generation = sum(generation_profile)
        capacity_factor_avg = np.mean([generation_profile[i] / (capacity_kw * 8760 / 1000) 
                                     for i in range(asset_life)])
        
        return {
            'lcoe_enhanced': lcoe,
            'lcoe_simple': simple_lcoe,
            'improvement_factor': simple_lcoe / lcoe,
            'wacc': wacc,
            'total_capex': capex,
            'total_generation_mwh': total_generation,
            'total_generation_pv_mwh': total_generation_pv,
            'capacity_factor_lifetime_avg': capacity_factor_avg,
            'technology': technology,
            'iso_code': iso_code,
            'asset_life_years': asset_life,
            'cash_flow_schedule': pd.DataFrame(cash_flows),
            'cost_breakdown': {
                'capex_per_mwh': (capex / (1 + wacc) ** 0) / total_generation_pv,
                'fixed_om_per_mwh': sum(cf['fixed_om'] * cf['discount_factor'] for cf in cash_flows) / total_generation_pv,
                'variable_om_per_mwh': sum(cf['variable_om'] * cf['discount_factor'] for cf in cash_flows) / total_generation_pv,
                'fuel_cost_per_mwh': sum(cf['fuel_cost'] * cf['discount_factor'] for cf in cash_flows) / total_generation_pv,
                'financing_cost_per_mwh': sum(cf['debt_service'] * cf['discount_factor'] for cf in cash_flows) / total_generation_pv,
                'policy_benefit_per_mwh': -policy_adjustments['revenue_benefit_per_mwh']  # Negative because it reduces costs
            },
            'policy_summary': {
                'capex_reduction_pct': policy_adjustments['capex_reduction'] * 100,
                'revenue_benefit_per_mwh': policy_adjustments['revenue_benefit_per_mwh'],
                'total_policy_value': (base_capex - capex) + (policy_adjustments['revenue_benefit_per_mwh'] * total_generation)
            }
        }
    
    def compare_technologies(self, scenarios: list, iso_code: str = 'USA') -> pd.DataFrame:
        """Compare multiple technology scenarios"""
        results = []
        
        for scenario in scenarios:
            result = self.calculate_enhanced_lcoe(
                scenario['technology'],
                scenario['capacity_factor'],
                scenario['capacity_kw'],
                iso_code,
                scenario.get('custom_params')
            )
            
            results.append({
                'technology': scenario['technology'],
                'capacity_factor': scenario['capacity_factor'],
                'capacity_kw': scenario['capacity_kw'],
                'lcoe_enhanced': result['lcoe_enhanced'],
                'lcoe_simple': result['lcoe_simple'],
                'wacc': result['wacc'],
                'total_generation_mwh': result['total_generation_mwh'],
                'capex_per_mwh': result['cost_breakdown']['capex_per_mwh'],
                'om_per_mwh': result['cost_breakdown']['fixed_om_per_mwh'] + result['cost_breakdown']['variable_om_per_mwh'],
                'fuel_per_mwh': result['cost_breakdown']['fuel_cost_per_mwh']
            })
        
        return pd.DataFrame(results).sort_values('lcoe_enhanced')

# Example usage and demonstration
if __name__ == "__main__":
    calculator = EnhancedLCOECalculator()
    
    # Example scenarios for comparison
    scenarios = [
        {
            'technology': 'solar',
            'capacity_factor': 0.22,
            'capacity_kw': 100000  # 100 MW
        },
        {
            'technology': 'wind',
            'capacity_factor': 0.35,
            'capacity_kw': 100000  # 100 MW
        },
        {
            'technology': 'gas_ccgt',
            'capacity_factor': 0.50,
            'capacity_kw': 100000  # 100 MW
        }
    ]
    
    print("🔬 Enhanced LCOE Analysis Comparison")
    print("="*50)
    
    # Compare technologies
    comparison = calculator.compare_technologies(scenarios, 'USA')
    print("\nTechnology Comparison (USA):")
    print(comparison[['technology', 'capacity_factor', 'lcoe_enhanced', 'lcoe_simple']].round(2))
    
    # Detailed analysis for solar
    solar_result = calculator.calculate_enhanced_lcoe('solar', 0.22, 100000, 'USA')
    print(f"\n📊 Detailed Solar Analysis:")
    print(f"Enhanced LCOE: ${solar_result['lcoe_enhanced']:.2f}/MWh")
    print(f"Simple LCOE: ${solar_result['lcoe_simple']:.2f}/MWh")
    print(f"WACC: {solar_result['wacc']:.1%}")
    print(f"Asset Life: {solar_result['asset_life_years']} years")
    
    print(f"\n💰 Cost Breakdown ($/MWh):")
    for component, cost in solar_result['cost_breakdown'].items():
        print(f"  {component.replace('_', ' ').title()}: ${cost:.2f}")