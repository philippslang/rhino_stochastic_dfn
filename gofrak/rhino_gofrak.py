import Rhino as rh
import rhinoscriptsyntax as rs
import scriptcontext as sc
import json
import copy
import random
import math
import os


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
        perim = rh.Geometry.Polyline([p1,p4,p2,p3,p1])
        perim_id = sc.doc.Objects.AddPolyline(perim)
        perim_nrbs = perim.ToNurbsCurve()
        srf = rh.Geometry.Brep.CreatePlanarBreps(perim_nrbs)[0]
        srf_id = sc.doc.Objects.AddBrep(srf)


def draw_fractures(fractures):
    for f in fractures:
        f.draw()


def to_fracture(data, id):
    center = Vector(data[0:3])
    nv = Vector(data[3:6])
    sv1 = Vector(data[6:9])
    sv2 = Vector(data[9:12])
    if id == 'ellipsoid':
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


def gofrak2rhino(f):
    fractures = []
    for l in f:
        ls = l.split('\t')
        if ls[0] == 'data-set': # header line
            continue
        fractures.append(to_fracture(ls[2:], ls[1]))
    draw_fractures(fractures)


if __name__ == '__main__':
    document()
    with open('stats_Dfn_sim1.txt') as f:
        gofrak2rhino(f)