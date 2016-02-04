import Rhino as rh
import rhinoscriptsyntax as rs
import scriptcontext as sc
import json
import copy
import random
import math
import os


class srfc_guids:
    def __init__(self):
        self.fractures = []
        self.boxes = []


def update_views():
    """Applies rendering and redraws all objects."""
    #[rs.ViewDisplayMode(view, 'Ghosted') for view in rs.ViewNames()]
    sc.doc.Views.Redraw()


def layer(lname):
    """Changes to given layer, creates if not yet existent."""
    if not rs.IsLayer(lname):
        rs.AddLayer(lname) 
    rs.CurrentLayer(lname)


def intersect_surfaces(guids):
    """Intersects all surfaces in model. Uses python cmd line, not api."""
    update_views()
    rs.UnselectAllObjects()
    layer('INTS_BOX')
    rs.SelectObjects(guids.boxes)
    rs.Command('_Intersect', echo=False)
    rs.UnselectAllObjects()
    layer('INTS')
    rs.SelectObjects(guids.fractures)
    rs.Command('_Intersect', echo=False)
    frac_isect_ids = rs.LastCreatedObjects()
    rs.UnselectAllObjects()
    if frac_isect_ids:
        for intid in frac_isect_ids:
            if rs.IsCurve(intid):
                rs.AddPoint(rs.CurveStartPoint(intid))
                rs.AddPoint(rs.CurveEndPoint(intid))
        rs.SelectObjects(frac_isect_ids)
        rs.Command('_Intersect', echo=False)


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
    surf_ids = []
    for i in range(6):
        layer(layers[i])
        cpts = rect_corner_pts(midpts[i], edge_length, normal=normals[i])
        surfid = surf(cpts)
        surf_ids += [surfid]
    return surf_ids


def uniform_variates(N, discrete_intervals=0):
    if not discrete_intervals:
        return [random.random() for i in range(N)]
    else:
        dx = 1./discrete_intervals
        return [random.randint(0,discrete_intervals)*dx for i in range(N)]


def power_law_variates(N, vmin, vmax, exponent):
    """Returns list of powerlaw distributed variates within bounds."""
    yvars = uniform_variates(N)
    return [((vmax**(exponent+1.) - vmin**(exponent+1.))*y + vmin**(exponent+1.))**(1./(exponent+1.)) for y in yvars]


def uniform_centers(N, edge_length, midpt, discrete_intervals=0):
    """Returns list of random rhino pts within cube of edge_length and midpoint."""
    hel = edge_length/2.
    ranvdvars = [uniform_variates(N, discrete_intervals) for xyz in range(3)]
    coords = [[midpt[xyz]+(ranvdvars[xyz][i]-0.5)*2.*hel for i in range(N)] for xyz in range(3)]
    return [rh.Geometry.Point3d(coords[0][i], coords[1][i], coords[2][i]) for i in range(N)]


def uniform_normals(N, discrete_intervals=0):
    """
    Returns list of random rhino vectors.
    
    http://mathworld.wolfram.com/SpherePointPicking.html, but with bottom half of sphere only.
    """
    u = uniform_variates(N, discrete_intervals)
    if discrete_intervals > 1:
        discrete_intervals -= 1
    v = uniform_variates(N, discrete_intervals)
    theta = [2.0*math.pi*u[i] for i in range(N)]
    phi = [math.acos(2.0*v[i]-1.0)/2.+math.pi/2. for i in range(N)]
    pts = [rh.Geometry.Point3d(math.cos(theta[i])*math.sin(phi[i]), math.sin(theta[i])*math.sin(phi[i]), math.cos(phi[i])) for i in range(N)]
    origin = rh.Geometry.Point3d(0,0,0)
    return [rs.VectorCreate(pts[i], origin) for i in range(N)]


def fracture_perimeter(plane, radius):
    """Fracture perimeter determines shape, circle here."""
    perim = rh.Geometry.Circle(plane, radius)
    perim_id = sc.doc.Objects.AddCircle(perim)
    return perim, perim_id


def fracture_surface(perim):
    """Adds fracture curve and surface, dispatches to fracture_perimeter for shape."""
    perim_nrbs = perim.ToNurbsCurve()  
    srf = rh.Geometry.Brep.CreatePlanarBreps(perim_nrbs)[0]
    srf_id = sc.doc.Objects.AddBrep(srf)
    return srf_id


def perimeter_pts(perim_id, ptsno):
    """Places points in equidistance segments along circular perimeter."""
    return rs.DivideCurve(perim_id, ptsno, create_points=True)


def populate(radii, centers, unorms, perimpts=0, polygon=False):
    """Generates circle and surface objects on dedicated layers, name hardcoded here."""
    lnames, srf_ids, perim_ids = [], [], []
    for i in range(len(radii)):
        layer('PERIMS')
        plane = rs.PlaneFromNormal(centers[i], unorms[i])
        perim, perim_id = fracture_perimeter(plane, radii[i])
        lname = 'FRACTURE{:0>5d}_S'.format(i)
        lnames += [lname] 
        layer(lname)
        srf_id = fracture_surface(perim)
        if perimpts:
            ppts = perimeter_pts(perim_id, perimpts)
            if polygon: # delete circle and replace by polygon, this should be optimized
                ppts.append(ppts[0]) # close polygon
                rs.DeleteObjects([perim_id, srf_id])
                layer('PERIMS')
                perim_id = rs.AddPolyline(ppts)
                layer(lname)
                srf_id = rs.AddPlanarSrf(perim_id)
        srf_ids.append(srf_id)
        perim_ids.append(perim_id)
    return lnames, srf_ids


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


def fracture_centers_inside(names, radii, centers, edge_length, midpt=(0,0,0)):
    hel = edge_length/2.
    names_i, radii_i = [], []
    for i in range(len(names)):
        pt = centers[i]
        inside = [pt[xyz] >= midpt[xyz]-hel and pt[xyz] <= midpt[xyz]+hel for xyz in range(3)]
        if not False in inside:
            names_i.append(names[i])
            radii_i.append(radii[i])
    return names_i, radii_i


def feport_json(names, radii, names_i, centers, unorms):
    fname = 'rhino_results.json'
    if os.path.isfile(fname):
        with open(fname) as f:
            results = json.load(f)
    else:
        results = dict()
    if 'network' not in results:
        results['network'] = dict()
    nresults = results['network']
    nresults['fracture centers inside L3'] = len(names_i)
    nresults['fracture centers total'] = len(names)
    results['fractures'] = dict()
    fresults = results['fractures']
    for i, n in enumerate(names):
        fresults[n] = dict()
        sfresults = fresults[n]
        sfresults['unit normal'] = [unorms[i][j] for j in range(3)]
        sfresults['center'] = [centers[i][j] for j in range(3)]
        sfresults['radius'] = radii[i]
    with open(fname, 'w') as f:
        f.write(json.dumps(results, indent=2, sort_keys=True))


def freport(names, radii, centers, edge_length, unorms, midpt=(0,0,0)):
    #TODO json output
    freport_write_single(names, radii, 'FractureNamesAndRadii.txt')
    freport_write_triple(names, centers, 'FractureNamesAndCenters.txt')
    names_i, radii_i = fracture_centers_inside(names, radii, centers, edge_length, midpt)
    freport_write_single(names_i, radii_i, 'FractureNamesAndRadiiInside.txt')
    feport_json(names, radii, names_i, centers, unorms)

def save(fname='csp'):
    rs.Command('_-SaveAs Version 3 '+fname+'.3dm')


def create_dfn(settings):
    """
    Settings:
    HL1 is half-length of outer box.
    HL2 is half-length of fracture center box.
    HL3 is half-length of inner box.
    """
    document()
    guids, midpt = srfc_guids(), (0,0,0)
    random.seed(settings['seed'])
    bsrf_ids = cube(settings['HL1']*2.)
    guids.boxes = bsrf_ids
    corner_points(settings['HL1']*2.)
    if settings['HL3 cube']:
        bsrf_ids = cube(settings['HL3']*2., '_INT')
        guids.boxes += bsrf_ids
        corner_points(settings['HL3']*2.)
    if not settings['uniform size rmax']:
        radii = power_law_variates(settings['N'], settings['rmin'], settings['rmax'], settings['exponent'])
    else:
        radii = [settings['rmax'] for i in range(settings['N'])]
    centers = uniform_centers(settings['N'], settings['HL2']*2., midpt, settings['center intervals'])
    unorms = uniform_normals(settings['N'], settings['pole intervals'])
    fnames, fsrf_ids = populate(radii, centers, unorms, settings['perimeter points'], settings['polygon'])
    guids.fractures = fsrf_ids
    intersect_surfaces(guids)
    update_views()
    freport(fnames, radii, centers, settings['HL3']*2., unorms)
    save()


if __name__ == '__main__':
    with open('rhino_settings.json', 'r') as f:
        settings = json.load(f)
    create_dfn(settings)