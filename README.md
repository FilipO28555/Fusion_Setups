# Deuteron-Triton Fusion Simulation with PIConGPU

This repository contains a comprehensive setup for simulating deuteron-triton (D-T) fusion reactions using PIConGPU (Particle-in-Cell on Graphics Processing Units). The setup includes advanced fusion rate analysis tools that compare theoretical predictions with simulation results.

## 🎯 Key Features

- **Realistic D-T Fusion Physics**: Uses Padé approximation for cross-sections with center-of-mass energy calculations
- **Automated Analysis**: Python scripts for theoretical rate calculation and simulation result analysis
- **Parameter Optimization**: Tools to find optimal simulation parameters for observable fusion events
- **Comprehensive Visualization**: Automatic generation of comparison plots and analysis reports
- **File Safety**: Automatic backup and restore of configuration files

## 📁 Repository Structure

```
Fusion_Setups/
├── 🔬 Core Simulation Files
│   ├── include/picongpu/param/    # PIConGPU configuration parameters
│   ├── etc/picongpu/             # TBG batch configuration files
│   ├── run.sh                    # Main simulation execution script
│   ├── cmakeFlags               # Compilation flags
│   └── compile.log              # Compilation output
│
├── 🐍 Analysis Tools
│   ├── fusion_rate_analyzer.py  # Main analysis script
│   ├── test_analyzer.py         # Functionality tests
│   ├── test_file_modification.py # File modification tests
│   ├── example_usage.py         # Usage examples
│   └── suggest_parameters.py    # Parameter optimization tool
│
├── 📊 Analysis Scripts
│   └── Analysys_script/
│       └── energyHistogram.py   # Particle energy analysis
│
└── 📚 Documentation
    ├── README.md                # This file
    └── README_fusion_analyzer.md # Detailed analyzer documentation
```

## 🚀 Quick Start

### 1. Check Current Setup
```bash
# Check fusion rate for your current parameters
python suggest_parameters.py
```

### 2. Run Basic Analysis
```bash
# Test basic functionality (no simulation)
python test_analyzer.py

# Run with optimized parameters for observable fusion
python fusion_rate_analyzer.py --density 1e26 --timesteps 100 --output-folder fusion_test
```

### 3. Automated Testing
```bash
# Test multiple parameter combinations
python fusion_rate_analyzer.py --auto-test
```

## 🔬 Physics Overview

### Current Simulation Setup
- **Particles**: Deuterons (γ=1.01, positive Y drift) + Tritons (γ=1.01, negative Y drift)
- **Fusion Products**: Neutrons + Helium-4 nuclei  
- **Collision Type**: Head-on relativistic collision
- **Cross-Section**: D-T fusion with Padé approximation

### Key Parameters
| Parameter | Current Value | Units | Description |
|-----------|---------------|--------|-------------|
| γ_deuteron | 1.01 | - | Lorentz factor (positive Y drift) |
| γ_triton | 1.01 | - | Lorentz factor (negative Y drift) |
| Density | 1×10²⁵ | m⁻³ | Base particle density |
| Timesteps | 2 | - | Simulation duration |
| Grid | 256×1024×256 | cells | Simulation volume |
| dt | 6.4×10⁻¹⁷ | s | Time step size |

### Physics Calculations
- **CM Energy**: E_cm = √[(E_d + E_t)² - (p_d - p_t)²c²] - (m_d + m_t)c²
- **Cross-Section**: σ = S(E)/(E × exp(BG/√E)) using Padé coefficients
- **Fusion Rate**: R = n_D × n_T × ⟨σv⟩

## 📊 Analysis Results

With current parameters (γ=1.01, ρ=1×10²⁵ m⁻³, 2 timesteps):
- **CM Energy**: ~45 MeV
- **Cross-Section**: ~0.126 mb  
- **Expected Fusions**: ~0.0002 (very low!)
- **Status**: 🔴 Too low for reliable observation

### Recommended Parameters for Observable Fusion:
| Scenario | Density | Timesteps | Expected Fusions | Status |
|----------|---------|-----------|------------------|--------|
| Quick Test | 1×10²⁶ m⁻³ | 100 | ~1.1 | 🟢 Good |
| Reliable | 1×10²⁶ m⁻³ | 500 | ~5.7 | 🟢 Excellent |
| Conservative | 5×10²⁵ m⁻³ | 200 | ~0.6 | 🟡 Moderate |

## 🛠️ Tools & Scripts

### Main Analysis Tool
- **`fusion_rate_analyzer.py`**: Complete fusion analysis pipeline
  - Updates simulation parameters
  - Calculates theoretical predictions  
  - Runs PIConGPU simulations
  - Analyzes results and generates plots

### Helper Scripts  
- **`suggest_parameters.py`**: Find optimal parameters for your setup
- **`test_analyzer.py`**: Test basic functionality
- **`example_usage.py`**: Usage examples and recommendations

## 📈 Usage Examples

```bash
# Check what parameters would work well
python suggest_parameters.py

# Run optimized simulation
python fusion_rate_analyzer.py \
    --gamma-d 1.01 --gamma-t 1.01 \
    --density 1e26 --timesteps 100 \
    --output-folder optimized_test

# Custom parameters
python fusion_rate_analyzer.py \
    --gamma-d 1.05 --gamma-t 1.03 \
    --density 5e25 --timesteps 200 \
    --output-folder custom_test

# Automated testing
python fusion_rate_analyzer.py --auto-test
```

## 🔧 Configuration Files

### Key Files Modified by Analysis Tools:
- **`particle.param`**: Gamma values for particle drifts
- **`simulation.param`**: Density and physical constants
- **`1.cfg`**: Grid size and simulation timesteps

### Safety Features:
- Automatic backup before modification
- Restore capability if simulation fails
- Parameter validation and warnings

## 📋 Prerequisites

- PIConGPU environment properly configured
- Python 3.6+ with NumPy, Pandas, Matplotlib
- Sufficient computational resources for desired simulation scale
- Write permissions for configuration files

## 🆘 Troubleshooting

### Low Fusion Rates
```bash
# Check current setup
python suggest_parameters.py

# If expected fusions < 0.1, increase:
# - Density: 5e25 → 1e26 → 5e26 m⁻³  
# - Timesteps: 100 → 500 → 1000
# - Or use lower gamma (closer to 1.0)
```

### Simulation Issues
- Check `compile.log` for compilation errors
- Verify PIConGPU environment variables
- Check disk space and file permissions

## 📚 Further Reading

- See `README_fusion_analyzer.md` for detailed technical documentation
- Check `Analysys_script/` for additional analysis tools
- Review PIConGPU documentation for advanced configuration

## 🎯 Current Branch: DT-nHe_uniform

This branch focuses on uniform deuteron-triton fusion with neutron and helium-4 production analysis.

1. Clone the repository
2. Switch to the desired branch (`main` or `static`)
3. Configure your simulation parameters in `include/picongpu/param/`
4. Build and run using the provided scripts

## Notes

- Build directories (`.build/`, `build/`) are excluded from version control
- Binary/executable directories (`bin/`) are excluded from version control
- Log files are also excluded from the repository
