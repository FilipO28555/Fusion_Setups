#!/usr/bin/env python3
"""
Core functions to compute D-T fusion reaction rate and total expected fusions
matching the PIConGPU kernel physics (sigma * v_rel * gamma_cm).

No dependencies beyond the standard library and numpy.
"""
from typing import Iterable, Tuple, Dict
import math

try:
    import numpy as np
except Exception:  # minimal fallback without numpy
    np = None

# Physical constants
C_LIGHT = 2.99792458e8           # m/s
AMU = 1.66053906660e-27          # kg
KEV_TO_JOULE = 1.602176634e-16   # J/keV
MILLI_BARN_TO_M2 = 1e-31         # m^2 per millibarn

# Particle masses (in AMU)
DEUTERON_MASS_AMU = 2.01410177812
TRITON_MASS_AMU   = 3.0160492779

# Padé parameters for D-T cross section (mb)
PADE_PARAMS = {
    'BG': 34.3827,
    'A1': 6.927e4,
    'A2': 7.454e8,
    'A3': 2.050e6,
    'A4': 5.2002e4,
    'A5': 0.0,
    'B1': 6.38e1,
    'B2': -9.95e-1,
    'B3': 6.981e-5,
    'B4': 1.728e-4,
}


def direction_cosine(dir_d: Iterable[float], dir_t: Iterable[float]) -> float:
    """Return the cosine of the angle between two 3D vectors.
    If a vector has zero norm, returns -1.0 by default (head-on).
    """
    try:
        ax, ay, az = dir_d
        bx, by, bz = dir_t
        a2 = ax*ax + ay*ay + az*az
        b2 = bx*bx + by*by + bz*bz
        if a2 <= 0.0 or b2 <= 0.0:
            return -1.0
        inva = 1.0 / math.sqrt(a2)
        invb = 1.0 / math.sqrt(b2)
        return (ax*bx + ay*by + az*bz) * inva * invb
    except Exception:
        return -1.0


def _safe_sqrt(x: float) -> float:
    return math.sqrt(x) if x > 0.0 else 0.0


def cm_quantities(
    gamma_d: float,
    gamma_t: float,
    dir_cos: float = -1.0,
    m_d_amu: float = DEUTERON_MASS_AMU,
    m_t_amu: float = TRITON_MASS_AMU,
) -> Dict[str, float]:
    """Compute CM-related quantities from Lorentz factors and geometry.

    Returns dict with: E_r_keV, gamma_r, v_rel (m/s), gamma_cm.
    """
    m0 = m_d_amu * AMU
    m1 = m_t_amu * AMU

    m0c2 = m0 * C_LIGHT * C_LIGHT
    m1c2 = m1 * C_LIGHT * C_LIGHT

    E0 = gamma_d * m0c2
    E1 = gamma_t * m1c2

    p0 = _safe_sqrt(E0*E0 - m0c2*m0c2) / C_LIGHT
    p1 = _safe_sqrt(E1*E1 - m1c2*m1c2) / C_LIGHT

    # magnitude of total momentum considering angle between p0 and p1
    p_tot_sq = p0*p0 + p1*p1 + 2.0*p0*p1*dir_cos
    p_tot = _safe_sqrt(p_tot_sq)

    E_tot = E0 + E1
    s = E_tot*E_tot - (p_tot * C_LIGHT) * (p_tot * C_LIGHT)
    s = max(s, 0.0)

    # Relative gamma (Cannoni eq. 42): gamma_r = (s - m0^2c^4 - m1^2c^4) / (2 m0 m1 c^4)
    gamma_r_num = s - m0c2*m0c2 - m1c2*m1c2
    gamma_r_den = 2.0 * m0c2 * m1c2
    gamma_r = gamma_r_num / gamma_r_den if gamma_r_den > 0.0 else 1.0
    if not (gamma_r >= 1.0):
        gamma_r = 1.0

    # Relative speed
    one_over_gamma_r2 = 1.0 / (gamma_r*gamma_r)
    v_rel = C_LIGHT * _safe_sqrt(1.0 - one_over_gamma_r2)

    # CM gamma: gamma_cm = E_tot / sqrt(s)
    sqrt_s = _safe_sqrt(s)
    gamma_cm = E_tot / sqrt_s if sqrt_s > 0.0 else 1.0

    # Reduced mass and CM relative kinetic energy
    mu = (m0 * m1) / (m0 + m1)
    E_r = mu * C_LIGHT * C_LIGHT * (gamma_r - 1.0)
    E_r_keV = E_r / KEV_TO_JOULE

    return {
        'E_r_keV': E_r_keV,
        'gamma_r': gamma_r,
        'v_rel': v_rel,
        'gamma_cm': gamma_cm,
    }


def dt_cross_section_mb(E_keV: float, p: Dict[str, float] = PADE_PARAMS) -> float:
    """D-T fusion cross section (millibarns) via Padé approximation.
    sigma(E) = S(E) / (E * exp(BG / sqrt(E)))
    """
    E = max(E_keV, 1e-12)
    S_num = (p['A1'] + E * (p['A2'] + E * (p['A3'] + E * (p['A4'] + E * p['A5']))))
    S_den = (1.0 + E * (p['B1'] + E * (p['B2'] + E * (p['B3'] + E * p['B4']))))
    S_E = S_num / S_den
    return S_E / (E * math.exp(p['BG'] / math.sqrt(E)))


def reaction_rate_invariant_flux(
    gamma_d: float,
    gamma_t: float,
    n_d: float,
    n_t: float,
    dir_cos: float = -1.0,
    m_d_amu: float = DEUTERON_MASS_AMU,
    m_t_amu: float = TRITON_MASS_AMU,
) -> Tuple[float, float, float, float, float]:
    """Return (rate, E_r_keV, sigma_mb, v_rel, gamma_cm).
    rate has units m^-3 s^-1 and uses sigma * v_rel * gamma_cm.
    """
    q = cm_quantities(gamma_d, gamma_t, dir_cos, m_d_amu, m_t_amu)
    sigma_mb = dt_cross_section_mb(q['E_r_keV'])
    sigma_m2 = sigma_mb * MILLI_BARN_TO_M2
    sigma_v = sigma_m2 * q['v_rel'] * q['gamma_cm']
    rate = n_d * n_t * sigma_v
    return rate, q['E_r_keV'], sigma_mb, q['v_rel'], q['gamma_cm']


def total_expected_fusions(
    reaction_rate: float,
    grid_size: Tuple[int, int, int],
    cell_width: float,
    cell_height: float,
    cell_depth: float,
    timesteps: int,
    dt: float,
) -> Tuple[float, float, float]:
    """Return (N_expected, volume, total_time).
    N_expected = rate * volume * total_time
    volume = (Nx*dx) * (Ny*dy) * (Nz*dz)
    total_time = timesteps * dt
    """
    Nx, Ny, Nz = grid_size
    volume = (Nx * cell_width) * (Ny * cell_height) * (Nz * cell_depth)
    total_time = timesteps * dt
    N_expected = reaction_rate * volume * total_time
    return N_expected, volume, total_time


__all__ = [
    'direction_cosine',
    'cm_quantities',
    'dt_cross_section_mb',
    'reaction_rate_invariant_flux',
    'total_expected_fusions',
]
