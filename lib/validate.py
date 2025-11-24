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

import sys
import os
from pathlib import Path

# Add the lib directory to path for imports
lib_path = Path(__file__).absolute().parent
sys.path.append(str(lib_path))

# Import and run the main validation function
if __name__ == "__main__":
    from validate_fusion import main
    main()
