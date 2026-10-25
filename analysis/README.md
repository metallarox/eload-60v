# Loop and thermal analysis

Small-signal model of one channel (OPA2196 + IXTH75N10L2 source follower + 20 mΩ shunt + R14/C6 integrator), solved symbolically with sympy and evaluated with scipy.

```
pip install -r requirements.txt
python loopz.py   # derive symbolic transfer functions -> h.pkl
python num.py     # phase / gain margin at several currents
python cl.py      # closed-loop bandwidth and small-signal step
python scan.py    # compensation sweep with worst-case parameters
python tsim.py    # large-signal time-domain simulation -> tsim.pkl
python plots.py   # figures used in docs/images
```

Assumptions: OPA2196 A0 = 120 dB, second pole 4.5 MHz, open-loop Ro = 300 Ω; gm from gfs = 44 S at 37.5 A (square law); DUT treated as an ideal voltage source.
