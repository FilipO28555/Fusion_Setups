import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import sys
import os

# Check for directory argument
if len(sys.argv) > 1:
    output_dir = sys.argv[1]
else:
    output_dir = '/home/optolo43'  # Default directory

# Ensure output directory exists
os.makedirs(output_dir, exist_ok=True)

# Read the CSV file
df = pd.read_csv('/home/optolo43/Fusion_Setups/Results/results.csv')

# Calculate relative error
df['relative_error_percent'] = ((df['measured_He4_final'] - df['predicted_events']) / df['predicted_events']) * 100

# Group by simulation setup (tag, gamma, E_rel_keV) to identify distinct experiments
df['setup_id'] = df.groupby(['tag', 'gamma', 'E_rel_keV']).ngroup()

# Create figure with subplots
fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))

# Color map for different setups
colors = plt.cm.Set1(np.linspace(0, 1, df['setup_id'].nunique()))

# Plot 1: Error vs PPC (all points)
for setup_id in df['setup_id'].unique():
    setup_data = df[df['setup_id'] == setup_id]
    setup_info = setup_data.iloc[0]
    label = f"{setup_info['tag']}: E={setup_info['E_rel_keV']:.0f} keV"
    
    ax1.scatter(setup_data['ppc'], setup_data['relative_error_percent'], 
               color=colors[setup_id], label=label, s=60, alpha=0.7)

ax1.set_xlabel('Particles Per Cell (ppc)')
ax1.set_ylabel('Relative Error (%)')
ax1.set_title('Relative Error vs Particles Per Cell')
ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
ax1.grid(True, alpha=0.3)

# Plot 2: Standard deviation vs PPC (calculated within each setup)
std_data = []
for setup_id in df['setup_id'].unique():
    setup_data = df[df['setup_id'] == setup_id]
    ppc_groups = setup_data.groupby('ppc')
    
    for ppc, group in ppc_groups:
        if len(group) > 1:  # Only calculate std if multiple measurements exist
            std_dev = group['measured_He4_final'].std()
            rel_std = (std_dev / group['measured_He4_final'].mean()) * 100
            setup_info = group.iloc[0]
            
            std_data.append({
                'setup_id': setup_id,
                'ppc': ppc,
                'std_dev': std_dev,
                'rel_std_percent': rel_std,
                'tag': setup_info['tag'],
                'energy_keV': setup_info['E_rel_keV'],
                'n_samples': len(group)
            })

if std_data:
    std_df = pd.DataFrame(std_data)
    
    for setup_id in std_df['setup_id'].unique():
        setup_std = std_df[std_df['setup_id'] == setup_id]
        setup_info = setup_std.iloc[0]
        label = f"{setup_info['tag']}: E={setup_info['energy_keV']:.0f} keV"
        
        ax2.scatter(setup_std['ppc'], setup_std['std_dev'], 
                   color=colors[setup_id], label=label, s=60, alpha=0.7)

    ax2.set_xlabel('Particles Per Cell (ppc)')
    ax2.set_ylabel('Standard Deviation of He4 Events')
    ax2.set_title('Standard Deviation vs Particles Per Cell')
    ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax2.grid(True, alpha=0.3)
    ax2.set_yscale('log')
else:
    ax2.text(0.5, 0.5, 'No multiple measurements\nper PPC value found', 
             ha='center', va='center', transform=ax2.transAxes)

# Plot 3: Error vs PPC for each energy regime separately
energy_regimes = df.groupby('E_rel_keV')
for energy, group in energy_regimes:
    mean_error = group.groupby('ppc')['relative_error_percent'].mean()
    std_error = group.groupby('ppc')['relative_error_percent'].std()
    
    ax3.errorbar(mean_error.index, mean_error.values, yerr=std_error.values,
                fmt='o-', label=f'E = {energy:.0f} keV', capsize=5)

ax3.set_xlabel('Particles Per Cell (ppc)')
ax3.set_ylabel('Mean Relative Error (%) ± Std Dev')
ax3.set_title('Mean Error vs PPC by Energy Regime')
ax3.legend()
ax3.grid(True, alpha=0.3)

# Plot 4: Absolute error vs PPC
for setup_id in df['setup_id'].unique():
    setup_data = df[df['setup_id'] == setup_id]
    setup_info = setup_data.iloc[0]
    label = f"{setup_info['tag']}: E={setup_info['E_rel_keV']:.0f} keV"
    
    abs_error = np.abs(setup_data['measured_He4_final'] - setup_data['predicted_events'])
    ax4.scatter(setup_data['ppc'], abs_error, 
               color=colors[setup_id], label=label, s=60, alpha=0.7)

ax4.set_xlabel('Particles Per Cell (ppc)')
ax4.set_ylabel('Absolute Error (He4 events)')
ax4.set_title('Absolute Error vs Particles Per Cell')
ax4.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
ax4.grid(True, alpha=0.3)
ax4.set_yscale('log')

plt.tight_layout()
output_path = os.path.join(output_dir, 'ppc_error_analysis.png')
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"Plot saved to: {output_path}")
plt.show()

# Print summary statistics
print("PPC Error Analysis Summary:")
print("=" * 50)
print(f"PPC range in dataset: {df['ppc'].min()} - {df['ppc'].max()}")
print(f"Number of unique setups: {df['setup_id'].nunique()}")
print("\nError statistics by setup:")
for setup_id in df['setup_id'].unique():
    setup_data = df[df['setup_id'] == setup_id]
    setup_info = setup_data.iloc[0]
    print(f"\n{setup_info['tag']} (E={setup_info['E_rel_keV']:.0f} keV):")
    print(f"  PPC range: {setup_data['ppc'].min()}-{setup_data['ppc'].max()}")
    print(f"  Error range: {setup_data['relative_error_percent'].min():.3f}% to {setup_data['relative_error_percent'].max():.3f}%")
    print(f"  Error std dev: {setup_data['relative_error_percent'].std():.3f}%")