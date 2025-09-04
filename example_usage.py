#!/usr/bin/env python3
"""
Example usage of the fusion rate analyzer with realistic parameters
"""

import sys
sys.path.append('/home/optolo43/Fusion_Setups')

from fusion_rate_analyzer import FusionRateAnalyzer

def example_low_energy_run():
    """Example run with low energy parameters."""
    print("=" * 60)
    print("EXAMPLE: Low Energy Fusion Rate Analysis")
    print("=" * 60)
    
    analyzer = FusionRateAnalyzer()
    
    # Test with very low gamma values for realistic fusion energies
    gamma_d = 1.001  # Very low Lorentz factor
    gamma_t = 1.001
    density = 1e25   # Standard density
    timesteps = 100  # More timesteps to see effects
    
    print(f"Testing with:")
    print(f"  γ_deuteron = {gamma_d}")
    print(f"  γ_triton = {gamma_t}")
    print(f"  Density = {density:.1e} m⁻³")
    print(f"  Timesteps = {timesteps}")
    
    # Calculate expected results
    expected = analyzer.calculate_expected_fusions(gamma_d, gamma_t, density, timesteps, analyzer.params['dt'])
    
    print(f"\nPhysics Results:")
    print(f"  CM Energy: {expected['E_cm_keV']:.2f} keV")
    print(f"  Cross Section: {expected['sigma_mb']:.3e} mb")
    print(f"  Reaction Rate: {expected['reaction_rate']:.3e} m⁻³s⁻¹")
    print(f"  Expected Fusions: {expected['N_expected']:.3e}")
    print(f"  Rate per timestep: {expected['rate_per_timestep']:.3e}")
    
    if expected['N_expected'] < 0.01:
        print(f"\n⚠️  WARNING: Expected fusion count is very low ({expected['N_expected']:.2e})")
        print("   Consider increasing density, timesteps, or gamma values for observable effects.")
    else:
        print(f"\n✓ Expected fusion count is reasonable for simulation")
    
    return expected

def example_parameter_sweep():
    """Show how fusion rates change with different parameters."""
    print("\n" + "=" * 60)
    print("PARAMETER SWEEP ANALYSIS")
    print("=" * 60)
    
    analyzer = FusionRateAnalyzer()
    
    # Test different scenarios
    scenarios = [
        {"name": "Very Low Energy", "gamma_d": 1.001, "gamma_t": 1.001, "density": 1e25, "timesteps": 100},
        {"name": "Low Energy", "gamma_d": 1.01, "gamma_t": 1.01, "density": 1e25, "timesteps": 100},
        {"name": "Medium Energy", "gamma_d": 1.1, "gamma_t": 1.1, "density": 1e25, "timesteps": 100},
        {"name": "High Density", "gamma_d": 1.01, "gamma_t": 1.01, "density": 1e26, "timesteps": 100},
        {"name": "Long Simulation", "gamma_d": 1.01, "gamma_t": 1.01, "density": 1e25, "timesteps": 1000},
    ]
    
    print(f"{'Scenario':<15} {'E_CM (keV)':<12} {'σ (mb)':<12} {'N_expected':<12} {'Observable?':<12}")
    print("-" * 70)
    
    for scenario in scenarios:
        expected = analyzer.calculate_expected_fusions(
            scenario['gamma_d'], scenario['gamma_t'], 
            scenario['density'], scenario['timesteps'], 
            analyzer.params['dt']
        )
        
        observable = "Yes" if expected['N_expected'] >= 0.1 else "No"
        
        print(f"{scenario['name']:<15} {expected['E_cm_keV']:<12.1f} {expected['sigma_mb']:<12.2e} "
              f"{expected['N_expected']:<12.2e} {observable:<12}")

def recommended_parameters():
    """Suggest good parameters for testing."""
    print("\n" + "=" * 60)
    print("RECOMMENDED SIMULATION PARAMETERS")
    print("=" * 60)
    
    analyzer = FusionRateAnalyzer()
    
    print("For observable fusion events, try these parameter combinations:")
    print()
    
    # Find parameters that give reasonable event rates
    recommendations = []
    
    for gamma in [1.01, 1.05, 1.1]:
        for density in [5e25, 1e26, 5e26]:
            for timesteps in [100, 500, 1000]:
                expected = analyzer.calculate_expected_fusions(gamma, gamma, density, timesteps, analyzer.params['dt'])
                if 0.1 <= expected['N_expected'] <= 1000:  # Reasonable range
                    recommendations.append({
                        'gamma': gamma,
                        'density': density,
                        'timesteps': timesteps,
                        'expected': expected['N_expected'],
                        'E_cm': expected['E_cm_keV']
                    })
    
    # Sort by expected count
    recommendations.sort(key=lambda x: x['expected'])
    
    for i, rec in enumerate(recommendations[:5]):  # Show top 5
        print(f"{i+1}. γ = {rec['gamma']}, ρ = {rec['density']:.1e} m⁻³, steps = {rec['timesteps']}")
        print(f"   → Expected: {rec['expected']:.1f} fusions, E_CM = {rec['E_cm']:.1f} keV")
        print()

if __name__ == "__main__":
    try:
        example_low_energy_run()
        example_parameter_sweep()
        recommended_parameters()
        
        print("=" * 60)
        print("READY TO RUN SIMULATIONS!")
        print("=" * 60)
        print()
        print("Example commands:")
        print("# Quick test with reasonable parameters:")
        print("python fusion_rate_analyzer.py --gamma-d 1.01 --gamma-t 1.01 --density 1e26 --timesteps 100 --output-folder quick_test")
        print()
        print("# Automated testing with multiple scenarios:")
        print("python fusion_rate_analyzer.py --auto-test")
        print()
        print("# High rate scenario for guaranteed observation:")
        print("python fusion_rate_analyzer.py --gamma-d 1.05 --gamma-t 1.05 --density 5e26 --timesteps 500 --output-folder high_rate_test")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
