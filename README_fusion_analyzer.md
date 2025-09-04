# Fusion Rate Analyzer for PIConGPU

A comprehensive Python script for analyzing deuteron-triton fusion rates in PIConGPU simulations.

## Features

- **Theoretical Rate Calculation**: Uses relativistic physics and Padé approximation for D-T fusion cross-sections
- **Parameter Management**: Automatically updates simulation configuration files
- **Simulation Execution**: Runs PIConGPU simulations with specified parameters
- **Results Analysis**: Extracts and analyzes particle counts from simulation output
- **Comparison**: Compares theoretical predictions with simulation results
- **Automated Testing**: Tests multiple parameter combinations
- **Visualization**: Generates plots comparing theory vs simulation

## Quick Start

### Basic Usage

```bash
# Run with default parameters
python fusion_rate_analyzer.py --output-folder my_test

# Specify custom parameters
python fusion_rate_analyzer.py \
    --gamma-d 1.05 \
    --gamma-t 1.03 \
    --density 5e25 \
    --timesteps 100 \
    --output-folder custom_test

# Run automated testing with multiple scenarios
python fusion_rate_analyzer.py --auto-test
```

### Testing the Script

```bash
# Test basic functionality (no simulation)
python test_analyzer.py

# Test file modification capabilities
python test_file_modification.py

# See recommended parameters
python example_usage.py
```

## Physics Background

### Cross-Section Calculation

The script uses the Padé approximation for D-T fusion cross-sections:

```
σ = S(E) / (E * exp(BG/√E))
```

Where:
- S(E) is the astrophysical S-factor 
- BG = 34.3827 (Gamow factor)
- E is the center-of-mass energy in keV

### Center-of-Mass Energy

For head-on collision of deuteron and triton:

```
E_CM = √[(E_d + E_t)² - (p_d - p_t)²c²] - (m_d + m_t)c²
```

### Fusion Rate

The theoretical fusion rate is:

```
R = n_D × n_T × <σv>
```

Where:
- n_D, n_T are particle densities
- <σv> is the reaction rate coefficient

## Configuration Files

The script modifies three key files:

1. **`particle.param`**: Gamma values for particle drifts
2. **`simulation.param`**: Physical constants (density, cell sizes, timestep)
3. **`1.cfg`**: Simulation parameters (grid size, timesteps)

## Output

### Console Output
- Theoretical predictions (CM energy, cross-section, expected fusions)
- Simulation progress
- Results comparison
- Rate ratios (simulation/theory)

### Generated Files
- **Analysis plots**: `fusion_analysis.png`
- **Test reports**: `fusion_test_report.txt` (for automated testing)
- **Simulation data**: PIConGPU output files

## Parameter Recommendations

Based on testing, for observable fusion events try:

| Scenario | γ_d | γ_t | Density | Timesteps | Expected Fusions |
|----------|-----|-----|---------|-----------|------------------|
| Low Energy | 1.01 | 1.01 | 1×10²⁶ | 500 | ~0.4 |
| Medium Energy | 1.05 | 1.05 | 5×10²⁵ | 200 | ~0.2 |
| High Rate | 1.05 | 1.05 | 5×10²⁶ | 500 | ~5.0 |

**Note**: Lower gamma values (closer to 1.0) give higher cross-sections but lower energies.

## Advanced Usage

### Custom Parameter Ranges

```python
from fusion_rate_analyzer import FusionRateAnalyzer

analyzer = FusionRateAnalyzer()

# Calculate expected results without running simulation
expected = analyzer.calculate_expected_fusions(
    gamma_d=1.05, gamma_t=1.03, 
    density=1e26, timesteps=100, dt=6.4e-17
)

print(f"Expected fusions: {expected['N_expected']:.3e}")
```

### Automated Testing with Custom Cases

```python
test_cases = [
    {'gamma_d': 1.01, 'gamma_t': 1.01, 'density': 1e26, 'timesteps': 200},
    {'gamma_d': 1.05, 'gamma_t': 1.05, 'density': 5e25, 'timesteps': 300},
    # Add more cases...
]

analyzer = FusionRateAnalyzer()
results = analyzer.automated_testing(test_cases)
```

## Requirements

- Python 3.6+
- NumPy
- Pandas
- Matplotlib
- PIConGPU environment
- Access to simulation configuration files

## File Structure

```
/home/optolo43/Fusion_Setups/
├── fusion_rate_analyzer.py      # Main script
├── test_analyzer.py            # Basic functionality tests
├── test_file_modification.py   # File modification tests
├── example_usage.py           # Usage examples
├── include/picongpu/param/    # PIConGPU configuration files
├── etc/picongpu/             # TBG configuration files
└── run.sh                    # Simulation execution script
```

## Troubleshooting

### Low Fusion Rates
If expected fusion count < 0.1:
- Increase density (try 5×10²⁵ to 1×10²⁶ m⁻³)
- Increase timesteps (try 500-1000)
- Use lower gamma values (closer to 1.0)

### Simulation Fails
- Check PIConGPU environment setup
- Verify file permissions
- Check available disk space
- Review compile.log and output.log

### Parameter Not Updating
- Ensure file write permissions
- Check file backup/restore process
- Verify regex patterns in configuration files

## Contributing

The script is designed to be modular and extensible:

- Add new cross-section models in `calculate_cross_section()`
- Implement different collision geometries in `calculate_cm_energy()`
- Add new analysis methods in `analyze_simulation_results()`
- Extend plotting capabilities in `plot_results()`

## License

This script is part of the PIConGPU ecosystem and follows the same licensing terms.
