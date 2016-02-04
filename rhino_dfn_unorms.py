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


if __name__ == '__main__':
    with open('rhino_results.json', 'r') as f:
        results = json.load(f)
    fresults = results['fractures']
    unorms = [fresults[fres]['unit normal'] for fres in fresults]
    document()
    unit_sphere()
    fracture_poles(unorms)
    update_views()