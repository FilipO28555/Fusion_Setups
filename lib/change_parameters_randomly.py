"""
Copyright 2024-2024 Filip Optolowicz

This file is part of PIConGPU.

PIConGPU is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

PIConGPU is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with PIConGPU.
If not, see <http://www.gnu.org/licenses/>.
"""

# Usage:
# This script changes:
#  - gamma              in file particle.param
#  - TYPICAL_PARTICLES_PER_CELL in file simulation.param
# gamma and ppc are randomly chosen from predefined lists
# and saves the configuration in the file ./simOutput/params.txt

# This script is run from the ../bin/ci.sh

# This script assumes that the files:
# simulation.param, particle.param
# are in the directory ../include/picongpu/param
# and that the output directory ./simOutput exists

import numpy as np
from fusion_lib import predict_he4_production
from pathlib import Path

paramsPath = Path(__file__).absolute().parent / "../include/picongpu/param"

def change_param_file(file_name, param_name, value):
    """Change a parameter in a PIConGPU parameter file"""
    filePath = paramsPath / file_name
    with open(filePath, "r") as f:
        lines = f.readlines()
    
    with open(filePath, "w") as f:
        for line in lines:
            if param_name + " = " in line:
                changedLine = line.split("=")[0] + "= " + str(value) + ";\n"
                f.write(changedLine)
            else:
                f.write(line)

def change_drift_param_gamma(file_name, struct_name, gamma_value):
    """Change gamma parameter in DriftParam structs"""
    filePath = paramsPath / file_name
    with open(filePath, "r") as f:
        content = f.read()
    
    # Find and replace gamma in the specific struct
    import re
    pattern = rf'(struct\s+{struct_name}.*?float_64\s+gamma\s*=\s*)[^;]+(;)'
    replacement = rf'\g<1>{gamma_value}_X\g<2>'
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    with open(filePath, "w") as f:
        f.write(content)

def changeParams(gamma, ppc):
    """Update simulation parameters"""
    # Update particles per cell in simulation.param
    change_param_file("simulation.param", "TYPICAL_PARTICLES_PER_CELL", ppc)
    
    # Update gamma in both DriftParam structs in particle.param
    change_drift_param_gamma("particle.param", "DriftParamNegative", gamma)
    change_drift_param_gamma("particle.param", "DriftParamPositive", gamma)

def main():
    """Main function to randomly select and set fusion parameters"""
    
    # Define parameter ranges for fusion testing
    gamma_values = [1.2, 1.35, 1.5, 1.75, 2.0]  # Reasonable range for fusion
    ppc_values = [10, 15, 20, 25, 30]  # Particles per cell options
    grid_size = (128, 128, 128)  # From 1.cfg
    steps = 200  # From 1.cfg
    
    # Randomly select parameters
    gamma = gamma_values[np.random.randint(len(gamma_values))]
    ppc = ppc_values[np.random.randint(len(ppc_values))]
    
    # Predict He4 production to ensure we have enough events
    min_he4_threshold = 1e-6  # Minimum threshold for detection
    max_attempts = 20
    attempts = 0
    
    while attempts < max_attempts:
        predicted_he4, params = predict_he4_production(gamma, ppc, grid_size, steps)
        
        if predicted_he4 > min_he4_threshold:
            break
            
        # If not enough He4, try higher energy/density
        if predicted_he4 <= min_he4_threshold:
            gamma = min(gamma * 1.1, max(gamma_values))
            ppc = min(ppc * 1.2, max(ppc_values))
            
        attempts += 1
    
    # Ensure integer ppc
    ppc = int(ppc)
    
    # Apply the changes
    changeParams(gamma, ppc)
    
    print(f"Parameters set:")
    print(f"  Gamma: {gamma:.3f}")
    print(f"  Particles per cell: {ppc}")
    print(f"  Predicted He4 production: {predicted_he4:.3e}")
    print(f"  Relative energy (CM): {params['E_rel_keV']:.3e} keV")
    
    # Save parameters in a file in the output directory ./simOutput
    with open("./simOutput/params.txt", "w") as f:
        f.write(f"gamma: {gamma}, ppc: {ppc}, predicted_he4: {predicted_he4:.3e}, ")
        f.write(f"E_rel_keV: {params['E_rel_keV']:.3e}")
    
    # Also save detailed parameters for validation
    with open("./simOutput/fusion_params.txt", "w") as f:
        f.write(f"# Fusion simulation parameters\\n")
        f.write(f"gamma = {gamma}\\n")
        f.write(f"ppc = {ppc}\\n")
        f.write(f"predicted_he4 = {predicted_he4:.6e}\\n")
        f.write(f"E_rel_keV = {params['E_rel_keV']:.6e}\\n")
        f.write(f"v_rel = {params['v_rel']:.6e}\\n")
        f.write(f"n_D = {params['n_D']:.6e}\\n")
        f.write(f"n_T = {params['n_T']:.6e}\\n")
        f.write(f"total_volume = {params['total_volume']:.6e}\\n")
        f.write(f"total_time = {params['total_time']:.6e}\\n")

if __name__ == "__main__":
    main()
