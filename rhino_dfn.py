import Rhino as rh
import rhinoscriptsyntax as rs
import scriptcontext as sc


def create_dfn(settings):
    pass
    
if __name__ == '__main__':
    with open('rhino_settings.json', 'r') as f:
        settings = json.load(f)
    create_dfn(settings)