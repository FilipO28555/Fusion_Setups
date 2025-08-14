# BunchFusion Setups for PIConGPU

This repository contains BunchFusion simulation setups for PIConGPU (Particle-in-Cell on Graphics Processing Units).

## Branches

- **main**: Contains the main BunchFusion setup from `FusionSetup`
- **static**: Contains the static BunchFusion setup from `FusionSetup_Static` (current branch)

## Structure (Static Branch)

```
├── bin/           # Executable files and scripts
├── etc/           # Configuration files and templates
├── include/       # PIConGPU parameter files (static setup)
├── lib/           # Python libraries and utilities
├── cmakeFlags     # CMake configuration flags
└── cmakeFlagsSetup # CMake setup flags
```

## Usage

1. Clone the repository
2. Switch to the desired branch (`main` or `static`)
3. Configure your simulation parameters in `include/picongpu/param/`
4. Build and run using the provided scripts

## Notes

- Build directories (`.build/`, `build/`) are excluded from version control
- Log files are also excluded from the repository
