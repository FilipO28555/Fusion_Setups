# BunchFusion Setups for PIConGPU

This repository contains BunchFusion simulation setups for PIConGPU (Particle-in-Cell on Graphics Processing Units).

## Branches

- **main**: Contains the main BunchFusion setup from `FusionSetup`
- **static**: Contains the static BunchFusion setup from `FusionSetup_Static`

## Structure

```
├── etc/           # Configuration files and templates
├── include/       # PIConGPU parameter files
├── cmakeFlags     # CMake configuration flags
├── cmakeFlagsSetup # CMake setup flags
└── compile_run.sh # Compilation and run script (main branch only)
```

## Usage

1. Clone the repository
2. Switch to the desired branch (`main` or `static`)
3. Configure your simulation parameters in `include/picongpu/param/`
4. Build and run using the provided scripts

## Notes

- Build directories (`.build/`, `build/`) are excluded from version control
- Binary/executable directories (`bin/`) are excluded from version control
- Log files are also excluded from the repository
