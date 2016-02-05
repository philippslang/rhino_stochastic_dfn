import Rhino as rh
import rhinoscriptsyntax as rs
import scriptcontext as sc
import json
import os
import System.Guid


def update_views():
    [rs.ViewDisplayMode(view, 'Ghosted') for view in rs.ViewNames()]
    sc.doc.Views.Redraw()


def fracture_poles(unorms):
    [rs.AddPoint(unorm) for unorm in unorms]


def document():
    """Brute-force new document, discard all unsaved changes."""
    rs.DocumentModified(False)
    rs.Command('_-New _None')


def unit_sphere():
    c, r = rh.Geometry.Point3d(0, 0, 0), 1.
    sphere = rh.Geometry.Sphere(c, r)
    if sc.doc.Objects.AddSphere(sphere)!= System.Guid.Empty:
        sc.doc.Views.Redraw()
        return rh.Commands.Result.Success
    return rh.Commands.Result.Failure


def getunorms():
    with open('rhino_results.json', 'r') as f:
            results = json.load(f)
    fresults = results['fractures']
    return [fresults[fres]['unit normal'] for fres in fresults]

def save(fname='poles'):
    rs.Command('_-SaveAs '+fname+'.3dm')


if __name__ == '__main__':
    bdir = os.getcwd()
    with open('rhino_settings.json', 'r') as f:
        settings = json.load(f)
    if settings['realizations'] < 2:
        unorms = getunorms()
    else:
        n, unorms = settings['realizations'], []
        for i in range(n):
            os.chdir(bdir)
            rdir = 'csp_{:0>5d}'.format(i)
            os.chdir(rdir)
            unorms += getunorms()
        os.chdir(bdir)
    document()
    unit_sphere()
    fracture_poles(unorms)
    update_views()
    save('{0}\poles'.format(bdir))