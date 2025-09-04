# Fusion Simulation Quick Reference

## 🎯 Current Status
- **Setup**: Deuteron-Triton fusion with γ=1.01 each
- **Problem**: Current parameters give very low fusion rate (~0.0002 expected fusions)
- **Solution**: Use the analyzer tools to optimize parameters

## ⚡ Quick Commands

```bash
# Check your current setup
python suggest_parameters.py

# Run optimized simulation (recommended)
python fusion_rate_analyzer.py --density 1e26 --timesteps 100 --output-folder test

# Test multiple scenarios
python fusion_rate_analyzer.py --auto-test
```

## 📊 Parameter Recommendations

| Goal | Density | Timesteps | Expected Fusions | Command |
|------|---------|-----------|------------------|---------|
| **Quick Test** | 1×10²⁶ | 100 | ~1.1 | `--density 1e26 --timesteps 100` |
| **Reliable** | 1×10²⁶ | 500 | ~5.7 | `--density 1e26 --timesteps 500` |
| **Conservative** | 5×10²⁵ | 200 | ~0.6 | `--density 5e25 --timesteps 200` |

## 🔧 Key Files

- **`fusion_rate_analyzer.py`** - Main analysis tool
- **`suggest_parameters.py`** - Find good parameters  
- **`README.md`** - Full documentation
- **`run.sh`** - Simulation execution

## 🎪 Current Physics
- **CM Energy**: ~45 MeV (γ=1.01 each)
- **Cross-Section**: ~0.126 mb
- **Collision**: Head-on deuteron vs triton

Good luck with your simulation! 🚀
