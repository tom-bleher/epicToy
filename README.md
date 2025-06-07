# epicToy: LGAD Charge Sharing Simulation

A GEANT4 simulation for studying charge sharing position reconstruction in LGAD pixel sensors.

## Physics Overview

### Detector Model
- **Geometry**: Pixelated silicon detector with aluminum pixel pads
- **Pixel Layout**: Configurable grid with $100\mu m$ pixel size and $500\mu m$ spacing by default
- **Active Volume**: $30\times 30 \mathrm{mm}^{2}$ silicon substrate ($50\mu m$ thickness)

### Charge Sharing Physics

When a particle deposits energy in the detector, the simulation models the following process:

1. **Electron Generation**: Number of electrons produced: $N_e = E_{dep} / E_{ion}$
2. **Amplification**: LGAD amplification factor of 20: $N_e' = N_e \times 20$
3. **Charge Distribution**: Total charge $Q_{tot} = N_e' \times e$ is distributed across a 9×9 pixel neighborhood

#### Charge Fraction Calculation

For each pixel in the neighborhood, the charge fraction is calculated using:

$$
\alpha_i = \tan^{-1}\left[\frac{\ell/2 \times \sqrt{2}}{\ell/2 \times \sqrt{2} + d_i}\right]
$$

$$
F_i = \frac{\alpha_i \times \ln(d_i/d_0)^{-1}}{\sum_j \alpha_j \times \ln(d_j/d_0)^{-1}}
$$

Where:
- $\ell$: pixel size
- $d_i$: distance from hit to pixel center
- $d_0=10\mu m$: reference distance

### Position Reconstruction

The simulation implements 2D Gaussian fitting for position reconstruction:

#### Central Row/Column Fitting
- **X-direction**: Fit Gaussian to charge distribution along central row
- **Y-direction**: Fit Gaussian to charge distribution along central column

#### Diagonal Fitting
- **Main diagonal**: Fit along main neighborhood matrix diagonal
- **Secondary diagonal**: Fit along secondary neighborhood matrix diagonal

All fits use the parameterized Gaussian function: 

$$
y(x) = A \exp\left(-\frac{(x-\mu)^2}{2\sigma^2}\right) + B
$$

Such that:

- A: peak amplitude
- $m$: center
- $\sigma$: width
- $\mathrm{FWHM}: 2\sqrt{2\ln2}\,\sigma$
- $B$: constant, vertical offset


And the parameterized Lorentzian function: 

$$
y(x) = \frac{A}{1+\bigl(\frac{x-m}{\gamma}\bigr)^2} + B
$$

Such that:

- $A$: peak amplitude
- $m$: center
- $\mathrm{FWHM}: 2\gamma$
- $B$: vertical offset

## Usage

### Interactive (GUI)
```bash
./epicToy
```

### Batch Mode
```bash
./epicToy -m ../macros/run.mac
```

## Project Structure

```
epicToy/
├── src/                    # Implementation files
│   ├── DetectorConstruction.cc  # Detector geometry
│   ├── EventAction.cc           # Event processing & charge sharing
│   ├── RunAction.cc             # ROOT output management
│   ├── 2DGaussianFitCeres.cc         # Fitting algorithms
│   └── ...
├── include/                # Header files
├── macros/                 # GEANT4 macro files
└── build/                  # Build directory
```
