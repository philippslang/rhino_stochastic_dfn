import Rhino as rh
import rhinoscriptsyntax as rs
import scriptcontext as sc
import json, copy, random, math, os


class Vector:
    def __init__(self, x, y, z):
        self.xyz = [float(x),float(x),float(x)]
    def __init__(self, xyz):
        self.xyz = [float(xyz[0]),float(xyz[1]),float(xyz[2])]
    def __add__(self, other):
        v = [self.xyz[i]+other.xyz[i] for i in range(3)]
        return Vector(v)
    def __sub__(self, other):
        v = [self.xyz[i]-other.xyz[i] for i in range(3)]
        return Vector(v)
    def __repr__(self):
        return '({0:9.3f},{1:9.3f},{2:9.3f})'.format(*self.xyz)
    def __len__(self):
        return 3
    def __getitem__(self,key):
        return self.xyz[key]


def draw_rectangle(five_pts):
    """Five points, counter-clockwise rotation, first node appears twice to close"""
    perim = rh.Geometry.Polyline(five_pts)
    perim_id = sc.doc.Objects.AddPolyline(perim)
    perim_nrbs = perim.ToNurbsCurve()
    srf = rh.Geometry.Brep.CreatePlanarBreps(perim_nrbs)[0]
    srf_id = sc.doc.Objects.AddBrep(srf)


class EllipsoidFracture:
    def __init__(self, center, nv, sv1, sv2):
        self.center = center
        self.nv = nv
        self.sv1 = sv1
        self.sv2 = sv2
    def draw(self):
        p1 = rs.coerce3dpoint(self.center+self.sv1)
        p2 = rs.coerce3dpoint(self.center+self.sv2)
        perim = rh.Geometry.Ellipse(rs.coerce3dpoint(self.center), p1, p2)
        perim_id = sc.doc.Objects.AddEllipse(perim)
        perim_nrbs = perim.ToNurbsCurve()  
        srf = rh.Geometry.Brep.CreatePlanarBreps(perim_nrbs)[0]
        srf_id = sc.doc.Objects.AddBrep(srf)


class RectangleFracture(EllipsoidFracture):
    def draw(self):
        plane = rs.PlaneFromNormal(rs.coerce3dpoint(self.center), self.nv)
        p1 = rs.coerce3dpoint(self.center+self.sv1+self.sv2)
        p2 = rs.coerce3dpoint(self.center-self.sv1-self.sv2)
        p3 = rs.coerce3dpoint(self.center+self.sv1-self.sv2)
        p4 = rs.coerce3dpoint(self.center-self.sv1+self.sv2)
        draw_rectangle([p1,p4,p2,p3,p1])


def layer(lname):
    """Changes to given layer, creates if not yet existent."""
    if not rs.IsLayer(lname):
        rs.AddLayer(lname) 
    rs.CurrentLayer(lname)


def draw_bounding_box(min_max_pts):
    """Creates bounding box from min max corner points"""
    pt_min, pt_max = min_max_pts
    cpts = [rh.Geometry.Point3d(pt_min),
            rh.Geometry.Point3d(pt_max),
            rh.Geometry.Point3d(pt_min[0], pt_min[1], pt_max[2]),
            rh.Geometry.Point3d(pt_min[0], pt_max[1], pt_max[2]),
            rh.Geometry.Point3d(pt_max[0], pt_min[1], pt_min[2]),
            rh.Geometry.Point3d(pt_max[0], pt_max[1], pt_min[2]),
            rh.Geometry.Point3d(pt_max[0], pt_min[1], pt_max[2]),
            rh.Geometry.Point3d(pt_min[0], pt_max[1], pt_min[2])]
    layers = ['BOUNDARY1','BOUNDARY2','BOUNDARY3','BOUNDARY4',
              'BOUNDARY5','BOUNDARY6']
    lcpts = [[cpts[2],cpts[3],cpts[7],cpts[0],cpts[2]],
             [cpts[6],cpts[1],cpts[5],cpts[4],cpts[6]],
             [cpts[4],cpts[5],cpts[7],cpts[0],cpts[4]],
             [cpts[6],cpts[1],cpts[3],cpts[2],cpts[6]],
             [cpts[6],cpts[2],cpts[0],cpts[4],cpts[6]],
             [cpts[1],cpts[3],cpts[7],cpts[5],cpts[1]]]
    for pt in cpts: # current layer
        sc.doc.Objects.AddPoint(pt)
    for l, pts in zip(layers,lcpts):
        layer(l) # new layer
        draw_rectangle(pts)


def draw_fractures(fractures):
    for f in fractures:
        f.draw()


def to_fracture(data, id):
    center = Vector(data[0:3])
    nv = Vector(data[3:6])
    sv1 = Vector(data[6:9])
    sv2 = Vector(data[9:12])
    if id == 'ellipse':
        return EllipsoidFracture(center,nv,sv1,sv2)
    else:
        return RectangleFracture(center,nv,sv1,sv2)


def save(fname='csp'):
    """Saves current doc as v3 rhino file"""
    rs.Command('_-SaveAs Version 3 '+fname+'.3dm')


def document():
    """Brute-force new document, discard all unsaved changes."""
    rs.DocumentModified(False)
    rs.Command('_-New _None')
    sc.doc.Views.Redraw()


def read_fractures(f):
    fractures = []
    for l in f:
        ls = l.split('\t')
        if ls[0] == 'data-set': # header line
            continue
        fractures.append(to_fracture(ls[2:], ls[1]))
    return fractures


def gofrak2rhino(f,j, fn):
    fractures = read_fractures(f)
    layer('FRACTURES')
    draw_fractures(fractures)
    bbmin = rh.Geometry.Point3d(*j['bounding box']['min'])
    bbmax = rh.Geometry.Point3d(*j['bounding box']['max'])
    layer('STANDARD')
    draw_bounding_box([bbmin,bbmax])
    save(fn)

if __name__ == '__main__':
    bd = os.getcwd()
    gsfname = 'rhino_settings.json'
    
    fname = 'stats_Dfn_sim1.txt'
    #fname = 'stats_Dfn_sim2.txt'
    document()
    lsfname = fname.replace('.txt','.json')
    if not os.path.isfile(lsfname):
        lsfname = gsfname
    with open(gsfname, 'r') as f:
        j = json.load(f)
    with open(fname, 'r') as f:        
        gofrak2rhino(f,j, os.path.join(bd,fname.replace('.txt','')))