import Rhino as rh
import rhinoscriptsyntax as rs
import scriptcontext as sc
import json
import copy
import random
import math


def update_views():
    """Applies rendering and redraws all objects."""
    #[rs.ViewDisplayMode(view, 'Ghosted') for view in rs.ViewNames()]
    sc.doc.Views.Redraw()


def layer(lname):
    """Changes to given layer, creates if not yet existent."""
    if not rs.IsLayer(lname):
        rs.AddLayer(lname) 
    rs.CurrentLayer(lname)


def intersect_surfaces():
    """Intersects all surfaces in model. Uses python cmd line, not api."""
    update_views()
    layer('INTS')
    rs.Command('_SelAll', echo=False)
    rs.Command('_Intersect', echo=False)
    rs.UnselectAllObjects()


def document():
    """Brute-force new document, discard all unsaved changes."""
    rs.DocumentModified(False)
    rs.Command('_-New _None')
    update_views()


def surf(cpts):
    """Creates a surface based on points list, returns GUID.""" 
    return rs.AddSrfPt(cpts)
    
    
def rect_corner_pts(midpt, edge_length, normal='x'):
    """
    Returns list of cornerpoints of a rectangle with midpoint,
    edge_length and normal to x/y/z axis in no particular order.
    """
    aidcs = range(3)
    del aidcs[['x', 'y', 'z'].index(normal)]
    cpts = [copy.deepcopy(midpt) for i in range(4)]
    sgns, isgns = [1.,1.,-1.,1.,-1.,-1.,1.,-1.], 0
    for i in range(4):
        for j in aidcs:
            cpts[i][j] += sgns[isgns]*edge_length/2.
            isgns += 1
    return cpts


def cube(edge_length, prefix='', midpt=(0,0,0)):
    """Creates cube surfaces with hardcoded layer convention of BOTTOM etc..."""
    midpts = [rh.Geometry.Point3d(midpt[0]-edge_length/2., midpt[1], midpt[2]),
              rh.Geometry.Point3d(midpt[0]+edge_length/2., midpt[1], midpt[2]),
              rh.Geometry.Point3d(midpt[0], midpt[1]-edge_length/2., midpt[2]),
              rh.Geometry.Point3d(midpt[0], midpt[1]+edge_length/2., midpt[2]),
              rh.Geometry.Point3d(midpt[0], midpt[1], midpt[2]-edge_length/2.),
              rh.Geometry.Point3d(midpt[0], midpt[1], midpt[2]+edge_length/2.),]
    normals = ['x', 'x', 'y', 'y', 'z', 'z']
    layers = ['LEFT', 'RIGHT', 'FRONT', 'BACK', 'BOTTOM', 'TOP']
    if prefix:
        layers = [l+prefix for l in layers]
    for i in range(6):
        layer(layers[i])
        cpts = rect_corner_pts(midpts[i], edge_length, normal=normals[i])
        surfid = surf(cpts)


def power_law_variates(N, vmin, vmax, exponent):
    """Returns list of powerlaw distributed variates within bounds."""
    yvars = [random.random() for i in range(N)]
    return [((vmax**(exponent+1.) - vmin**(exponent+1.))*y + vmin**(exponent+1.))**(1./(exponent+1.)) for y in yvars]


def uniform_centers(N, edge_length, midpt):
    """Returns list of random rhino pts within cube of edge_length and midpoint."""
    hel = edge_length/2.
    coords = [[midpt[xyz]+(random.random()-0.5)*2.*hel for i in range(N)] for xyz in range(3)]
    return [rh.Geometry.Point3d(coords[0][i], coords[1][i], coords[2][i]) for i in range(N)]


def uniform_normals(N):
    """Returns list of random rhino vectors."""
    norms = [[random.random()-0.5 for i in range(N)] for xyz in range(3)]
    pts = [rh.Geometry.Point3d(norms[0][i], norms[1][i], norms[2][i]) for i in range(N)]
    origin = rh.Geometry.Point3d(0,0,0)
    return [rs.VectorUnitize(rs.VectorCreate(pts[i], origin)) for i in range(N)]


def fracture_perimeter(p, r):
    """Fracture perimeter determines shape, circle here."""
    perim = rh.Geometry.Circle(p, r)
    sc.doc.Objects.AddCircle(perim)
    return perim


def fracture(r, c, u):
    """Adds fracture curve and surface, dispatches to fracture_perimeter for shape."""
    p = rs.PlaneFromNormal(c, u)
    fp = fracture_perimeter(p, r)
    crv = fp.ToNurbsCurve()
    srf = sc.doc.Objects.AddBrep(rh.Geometry.Brep.CreatePlanarBreps(crv)[0])
    return crv, srf


def perimeter_pts(p, r, ptsno):
    """Places points in equidistance segments along circular perimeter."""
    pnorm = 2.*math.pi*r
    sleng = pnorm/ptsno
    return rs.DivideCurve(p, ptsno, create_points=True)


def populate(radii, centers, unorms, perimpts=0):
    """Generates circle and surface objects on dedicated layers, name hardcoded here."""
    lnames = []
    for i in range(len(radii)):
        lname = 'FRACTURE'+str(i)+'_S'
        lnames += [lname]
        layer(lname)
        perim, srf = fracture(radii[i], centers[i], unorms[i])
        if perimpts:
            perimeter_pts(perim, radii[i], perimpts)
    return lnames


def populate_powerlaw(N, rmin, rmax, exponent, edge_length, perimpts=0, midpt=(0,0,0)):
    """Populates cube space with truncated powerlaw size distributed fractures."""
    radii = power_law_variates(N, rmin, rmax, exponent)
    centers = uniform_centers(N, edge_length, midpt)
    unorms = uniform_normals(N)
    fnames = populate(radii, centers, unorms, perimpts)
    return radii, centers, fnames


def corner_points(edge_length, midpt=(0,0,0)):
    layer('Default')
    hel = edge_length/2.
    rs.AddPoint((midpt[0]+hel,midpt[1]+hel,midpt[2]+hel))
    rs.AddPoint((midpt[0]+hel,midpt[1]+hel,midpt[2]-hel))
    rs.AddPoint((midpt[0]+hel,midpt[1]-hel,midpt[2]-hel))
    rs.AddPoint((midpt[0]-hel,midpt[1]-hel,midpt[2]-hel))
    rs.AddPoint((midpt[0]-hel,midpt[1]-hel,midpt[2]+hel))
    rs.AddPoint((midpt[0]-hel,midpt[1]+hel,midpt[2]+hel))
    rs.AddPoint((midpt[0]-hel,midpt[1]+hel,midpt[2]-hel))
    rs.AddPoint((midpt[0]+hel,midpt[1]-hel,midpt[2]+hel))


def freport_write_single(names, prop, fname):
    lines = [names[i]+'\t'+str(prop[i])+'\n' for i in range(len(names))]
    with open(fname, 'w') as f:
        f.writelines(lines)


def freport_write_triple(names, prop, fname):
    lines = [names[i]+'\t'+str(prop[i][0])+'\t'+str(prop[i][1])+'\t'+str(prop[i][2])+'\n' for i in range(len(names))]
    with open(fname, 'w') as f:
        f.writelines(lines)


def freport(names, radii, centers):
    freport_write_single(names, radii, 'FractureNamesAndRadii.txt')
    freport_write_triple(names, centers, 'FractureNamesAndCenters.txt')


def create_dfn(settings):
    """
    Settings:
    HL1 is half-length of outer box.
    HL2 is half-length of fracture center box.
    HL3 is half-length of inner box.
    """
    document()
    random.seed(settings['seed'])
    cube(settings['HL1']*2.)
    corner_points(settings['HL1']*2.)
    if settings['HL3 cube']:
        cube(settings['HL3']*2., '_INT')
        corner_points(settings['HL3']*2.)
    radii, centers, fnames = populate_powerlaw(settings['N'], settings['rmin'], settings['rmax'], 
                                               settings['exponent'], settings['HL2']*2.,
                                               settings['perimeter points'])
    intersect_surfaces()    
    update_views()
    freport(fnames, radii, centers)
    print 'done...'


if __name__ == '__main__':
    with open('rhino_settings.json', 'r') as f:
        settings = json.load(f)
    create_dfn(settings)