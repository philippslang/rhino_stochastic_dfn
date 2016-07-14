import Rhino as rh
import rhinoscriptsyntax as rs
import scriptcontext as sc
import json, copy, random, math, os, glob, sys


def intersections():
    """Intersects all surfaces in model. Uses python cmd line, not api."""
    sc.doc.Views.Redraw()
    layer('INTERSECTIONS')
    objs = rs.AllObjects()
    rs.SelectObjects(objs)
    rs.Command('_Intersect', echo=False)
    frac_isect_ids = rs.LastCreatedObjects()
    rs.UnselectAllObjects()
    if frac_isect_ids:
        for intid in frac_isect_ids:
            if rs.IsCurve(intid):
                rs.AddPoint(rs.CurveStartPoint(intid))
                rs.AddPoint(rs.CurveEndPoint(intid))
        if len(frac_isect_ids) > 1:
            rs.SelectObjects(frac_isect_ids)
            rs.Command('_Intersect', echo=False)


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
        pts = [p1,p4,p2,p3,p1]
        draw_rectangle(pts)
        for pt in pts[0:-1]:
            sc.doc.Objects.AddPoint(pt)


class FractureSet:
    def __init__(self):
        self.f = []
    def append(self, f):
        self.f.append(f)
    def __getitem__(self,i):
        return self.f[i]
    def __len__(self):
        return len(self.f)
    def draw(self):
        for f in self.f:
            f.draw()
    def minmax_centers(self):
        m = sys.float_info.max
        mincomps = rh.Geometry.Point3d(m,m,m)
        maxcomps = rh.Geometry.Point3d(-m,-m,-m)
        for f in self.f:
            for d in range(3):
                mincomps[d] = min(f.center[d], mincomps[d])
                maxcomps[d] = max(f.center[d], maxcomps[d])
        return mincomps, maxcomps


class FractureSets:
    def __init__(self):
        self.f = {}
    def __getitem__(self, key):
        if key not in self.f:
            self.f[key] = FractureSet()
        return self.f[key]
    def __iter__(self):
        return iter(self.f)
    def draw(self):
        for f in self.f:
            layer(f)
            self.f[f].draw()
    def minmax_centers(self):
        m = sys.float_info.max
        mincomps = rh.Geometry.Point3d(m,m,m)
        maxcomps = rh.Geometry.Point3d(-m,-m,-m)
        for s in self.f:
            smin, smax = self.f[s].minmax_centers()
            for d in range(3):
                mincomps[d] = min(smin[d], mincomps[d])
                maxcomps[d] = max(smax[d], maxcomps[d])
        return mincomps, maxcomps


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


def draw_fracture_sets(fractures):
    fractures.draw()


def to_fracture(data, id):
    center = Vector(data[0:3])
    nv = Vector(data[3:6])
    sv1 = Vector(data[6:9])
    sv2 = Vector(data[9:12])
    if id == 'ellipse':
        return EllipsoidFracture(center,nv,sv1,sv2)
    else:
        return RectangleFracture(center,nv,sv1,sv2)


def save_document(fname='csp'):
    """Saves current doc as v3 rhino file"""
    rs.Command('_-SaveAs Version 3 '+fname+'.3dm')


def new_document():
    """Brute-force new document, discard all unsaved changes."""
    rs.DocumentModified(False)
    rs.Command('_-New _None')
    sc.doc.Views.Redraw()


def read_fracture_sets(f):
    fractures = FractureSets()
    for l in f:
        ls = l.split('\t')
        if ls[0] == 'data-set': # header line
            continue
        set_name = 'FRACTURES'     
        if ls[0] != '':
            set_name = ls[0].split('_')[1]
        fractures[set_name].append(to_fracture(ls[3:], ls[2]))
    return fractures


def minmax_fracture_centers(fracture_sets, rf=0.0):
    mi, ma = fracture_sets.minmax_centers()
    rfs = [(ma[d]-mi[d])*rf for d in range(3)]
    for d in range(2): # xy only
        mi[d] += rfs[d]
        ma[d] -= rfs[d]
    return mi, ma


def in_bbox(pt, pts):
    for i in range(3):
        if pt[i] < pts[0][i] or pt[i] > pts[1][i]:
            return False
    return True
    
    
def remove_fractures_outside(fsets, fbbpts, omit_sets):
    rfsets = FractureSets()
    for fset in fsets:
        rfset = rfsets[fset]
        if fset in omit_sets:
            for f in fsets[fset]:
                rfset.append(f)
            continue
        for f in fsets[fset]:
            if in_bbox(f.center, fbbpts):
                rfset.append(f)
    return  rfsets


def gofrak2rhino(f,j):
    """Dispatches settings, limits settings invasiveness"""
    fsets = read_fracture_sets(f)
    if 'fracture box' in j:
        fbbpts = [rh.Geometry.Point3d(*j['fracture box'][mm]) for mm in ['min','max']]
        omit_sets = j['fracture box']['omit']
        fsets = remove_fractures_outside(fsets, fbbpts, omit_sets)
    draw_fracture_sets(fsets)
    if 'auto bounding box' in j:
        if j['auto bounding box']:
            bbpts = minmax_fracture_centers(fsets, j['auto bounding box reduce'])
        else:
            bbpts = [rh.Geometry.Point3d(*j['bounding box'][mm]) for mm in ['min','max']]
    layer('STANDARD')
    draw_bounding_box(bbpts)
    intersections()


if __name__ == '__main__':
    bd = os.getcwd()
    gsfname = 'rhino_settings.json'
    
    fnames = ['stats_Dfn_sim1.txt', 'stats_Dfn_sim2.txt']
    fnames = glob.glob('stats_Dfn*.txt')
    fnames = glob.glob('sim_Dfn_sim*.txt')
    fnames = glob.glob('sim_Dfn*.txt')
    
    for fname in fnames:
        os.chdir(bd)
        fname_base = fname.replace('.txt','')
        # if a json file with same prifx as gofrak file is
        # found, this is used as settings file. gsfname otherwise
        lsfname = fname.replace('.txt','.json')
        try:
            with open(lsfname, 'r') as f:
                j = json.load(f)
        except:
            with open(gsfname, 'r') as f:
                j = json.load(f)        
        try: # create a directory for the rhino file
            os.mkdir(fname_base)
        except  OSError:
            pass        
        os.chdir(fname_base) # step in and run
        sd = os.getcwd()
        new_document()
        with open(os.path.join(bd, fname), 'r') as f:        
            gofrak2rhino(f,j)
        save_document(os.path.join(sd, fname_base))
