

def fusion_rate_per_V(cross_section, relative_velocity, n1, n2, *, identical_species = False)
    """
    Compute the fusion reaction rate per unit volume.
    R = <sigma v> * n1 * n2
    """
    rate = cross_section * relative_velocity * n1 * n2
    if identical_species:
        rate *= 0.5
    return rate

N1 = N2 = 1e26
dt = 1e-15
length = 1e-6
V = length**3




