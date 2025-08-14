# BunchFusion Setups for PIConGPU

This repository contains BunchFusion simulation setups for PIConGPU (Particle-in-Cell on Graphics Processing Units).

## Branches

- **main**: Contains the main BunchFusion setup from `FusionSetup`
- **static**: Contains the static BunchFusion setup from `FusionSetup_Static` (current branch)

## Structure (Static Branch)

```
├── etc/           # Configuration files and templates
├── include/       # PIConGPU parameter files (static setup with extended parameters)
├── lib/           # Python libraries and utilities
├── cmakeFlags     # CMake configuration flags
└── cmakeFlagsSetup # CMake setup flags
```

## Static Branch Features

- Extended parameter files including collision, dimension, fieldSolver, and precision parameters
- Python beam relaxation verification tools in `lib/python/picongpu/`
- Additional particle filters and species definitions

## Usage

1. Clone the repository
2. Switch to the desired branch (`main` or `static`)
3. Configure your simulation parameters in `include/picongpu/param/`
4. Build and run using the provided scripts

## Notes

- Build directories (`.build/`, `build/`) are excluded from version control
- Binary/executable directories (`bin/`) are excluded from version control
- Log files are also excluded from the repository
