## rhino_stochastic_dfn

Discrete fracture netwokrs in Rhino

### Usage 
Controlls in `rhino_settings.json`, needs to be in wrking directory. Script called through Rhino. A sample settings file can be found in the root directory, parameters are explained here (don't cpy-paste, hashtags are not JSON compatible).
```
{
  "HL1": 82.5,                # half-length of outer-most box
  "HL2": 52.5,                # half-length of fracture center domain box
  "HL3": 37.5,                # half-length of inner box, only used if "HL3 cube": true
  "rmax": 15.0,               # maximum fracture radius
  "rmin": 5.0,                # minimum fracture radius
  "exponent": -2.0,           # fracture radii distribution power-law exponent
  "N": 50,                    # total number of fractures created
  "seed": 0,                  # seed, should allow for reproducible geometries, at least within one system
  "HL3 cube": true,           # whether and inner cube is to be constructed
  "perimeter points": 6,      # points added along fracture perimeter line
  "polygon": false            # fracture converted from circle to n-polygon, where n = "perimeter points"
  "pole intervals": 0,        # random intervals for fracture poles in unit sphere surface space, if 0 continuous
  "center intervals": 0,      # random intervals for fracture poles in unit sphere surface space, if 0 continuous
  "uniform size rmax": false  # uniform fracture size (no powerlaw) of rmax
}
```

Hashtag comments in the code above have to be removed as they are not JSON compatible. The parameters `HL1-3` can be illustrated as follows. If `"HL3 cube": false` no inner cube will be created and `"HL3"` is ignored, ie, need not be in the JSON settings file.

<p align="left">
  <img src="https://raw.githubusercontent.com/plang85/rhino_stochastic_dfn/master/doc/rhino_dfn.png" height="400">
  <br/>
</p>
For legacy support reasons this program outputs `FractureNamesAndRadii.txt` and `FractureNamesAndCenters.txt`.
