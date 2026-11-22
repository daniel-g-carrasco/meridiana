"""Stream seeded IFC4 geometry to a target byte size, with bounded generator memory.

IfcOpenShell builds a valid floor prototype; entity references and GUIDs are remapped
for every floor. Size comes from actual swept solids, never comments or property padding.
Synthetic geometry is CC0-1.0. Sizes use decimal MB/GB; output files are never replaced.
"""
import argparse
from pathlib import Path
import random
import re
import uuid


def generate(path, size=50_000_000, seed=1):
    import ifcopenshell
    import ifcopenshell.guid
    rng = random.Random(seed)
    f = ifcopenshell.file(schema='IFC4')
    def guid(key):
        return ifcopenshell.guid.compress(uuid.uuid5(uuid.NAMESPACE_URL, f'meridiana:ifc:{seed}:{key}').hex)
    def root(kind, name):
        return f.create_entity(kind, GlobalId=guid(f'{kind}:{name}'), Name=name)
    def axis(x=0., y=0., z=0.):
        return f.createIfcAxis2Placement3D(f.createIfcCartesianPoint((float(x), float(y), float(z))), None, None)
    origin = axis()
    context = f.createIfcGeometricRepresentationContext(None, 'Model', 3, 1e-5, origin, None)
    units = f.createIfcUnitAssignment([f.createIfcSIUnit(None, 'LENGTHUNIT', None, 'METRE'),
                                     f.createIfcSIUnit(None, 'AREAUNIT', None, 'SQUARE_METRE'),
                                     f.createIfcSIUnit(None, 'VOLUMEUNIT', None, 'CUBIC_METRE')])
    project = root('IfcProject', 'Synthetic geometry CC0-1.0')
    project.RepresentationContexts, project.UnitsInContext = [context], units
    site, building = root('IfcSite', 'Neutral plain'), root('IfcBuilding', 'Synthetic complex')
    for parent, child in ((project, site), (site, building)):
        rel = root('IfcRelAggregates', child.Name)
        rel.RelatingObject, rel.RelatedObjects = parent, [child]
    base = max(e.id() for e in f)
    storey = root('IfcBuildingStorey', 'Floor')
    placement = f.createIfcLocalPlacement(None, axis())
    origin_id = placement.RelativePlacement.Location.id()
    storey.ObjectPlacement, storey.Elevation = placement, 0.
    rel = root('IfcRelAggregates', 'Floor aggregation')
    rel.RelatingObject, rel.RelatedObjects = building, [storey]
    products = []
    kinds = [('IfcWall', (6., .25, 3.4), 30), ('IfcSlab', (56., 40., .25), 2),
             ('IfcRoof', (28., 40., .3), 4), ('IfcPipeSegment', (.15, 12., .15), 24),
             ('IfcDuctSegment', (.6, 12., .4), 24), ('IfcFurnishingElement', (1.2, .8, .8), 45),
             ('IfcCurtainWall', (3., .1, 3.2), 20)]
    for kind, dimensions, count in kinds:
        for index in range(count):
            width, depth, height = dimensions
            product = root(kind, f'{kind[3:]} {index}')
            product.ObjectPlacement = f.createIfcLocalPlacement(placement, axis(
                index % 8*7+rng.uniform(0, .1), index//8*6, 3.5 if kind == 'IfcRoof' else 0.))
            solid_axis = axis()
            if kind == 'IfcRoof' and index % 2:
                solid_axis.Axis = f.createIfcDirection((0., -.2, 1.))
            profile = f.createIfcRectangleProfileDef('AREA', None, None, width, depth)
            solid = f.createIfcExtrudedAreaSolid(profile, solid_axis, f.createIfcDirection((0., 0., 1.)), height)
            body = f.createIfcShapeRepresentation(context, 'Body', 'SweptSolid', [solid])
            product.Representation = f.createIfcProductDefinitionShape(None, None, [body])
            products.append(product)
    rel = root('IfcRelContainedInSpatialStructure', 'Floor contents')
    rel.RelatedElements, rel.RelatingStructure = products, storey
    text = f.to_string()
    header = text.split('DATA;')[0]
    header = re.sub(r"FILE_NAME\(.*?\);", "FILE_NAME('synthetic.ifc','2026-01-01T00:00:00',('Daniel Grasso'),"
                    "('Meridiana'),'IfcOpenShell','Meridiana synthetic generator','CC0-1.0');", header, flags=re.S)
    rows = [line for line in text.split('DATA;')[1].split('ENDSEC;')[0].splitlines() if line.startswith('#')]
    shared = [line for line in rows if int(line[1:line.index('=')]) <= base]
    template = [line for line in rows if int(line[1:line.index('=')]) > base]
    maximum = max(e.id() for e in f)
    roots = [e.GlobalId for e in f.by_type('IfcRoot') if e.id() > base]
    reference = re.compile(r'#(\d+)')
    byte_count, floors = 0, 0
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        data = (header+'DATA;\n'+'\n'.join(shared)+'\n').encode('ascii')
        stream.write(data)
        byte_count += len(data)
        while byte_count < size:
            offset = floors*maximum
            gids = {value: guid(f'floor:{floors}:{value}') for value in roots}
            chunk = []
            for line in template:
                original_id = int(line[1:line.index('=')])
                if original_id == origin_id:
                    line = f'#{origin_id}=IFCCARTESIANPOINT(({floors % 10*70}.,{floors//120*60}.,{floors//10 % 12*4}.));'
                line = reference.sub(lambda m, offset=offset: '#'+str(int(m[1])+(offset if int(m[1]) > base else 0)), line)
                for value in re.findall(r"'([0-3][0-9A-Za-z_$]{21})'", line):
                    if value in gids:
                        line = line.replace(value, gids[value])
                chunk.append(line)
            data = ('\n'.join(chunk)+'\n').encode('ascii')
            stream.write(data)
            byte_count += len(data)
            floors += 1
        stream.write(b'ENDSEC;\nEND-ISO-10303-21;\n')
    return dict(seed=seed, bytes=path.stat().st_size, floors=floors, products=floors*len(products), license='CC0-1.0')


def byte_size(value):
    match = re.fullmatch(r'(\d+(?:\.\d+)?)\s*(MB|GB|KB|B)?', value.upper())
    if not match:
        raise argparse.ArgumentTypeError('size: e.g. 50MB, 300MB, 1GB')
    return int(float(match[1])*{'B': 1, 'KB': 1000, 'MB': 1_000_000, 'GB': 1_000_000_000}[match[2] or 'MB'])


if __name__ == '__main__':
    import json
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seed', type=int, default=1)
    p.add_argument('--size', type=byte_size, default=50_000_000)
    p.add_argument('--out', required=True, type=Path)
    args = p.parse_args()
    print(json.dumps(generate(args.out, args.size, args.seed)))
