from math import cos,radians,hypot
from .checkpoints import haversine

def grid(geometries):
    lengths = [sum(haversine(a,b) for a,b in zip(g,g[1:])) for g in geometries]
    spacing = max(40000,sum(lengths)/35)
    points = set()
    for geometry in geometries:
        remaining = 0.0
        for a,b in zip(geometry,geometry[1:]):
            distance = haversine(a,b)
            # Perpendicular in a local equirectangular frame, including east-west roads.
            scale = max(.2,cos(radians((a[1]+b[1])/2)))
            dx,dy = (b[0]-a[0])*scale,b[1]-a[1]
            length = hypot(dx,dy)
            nx,ny = (-dy/length,dx/length) if length else (1,0)
            while remaining <= distance:
                f = remaining/distance if distance else 0
                lon,lat = [a[j]+f*(b[j]-a[j]) for j in range(2)]
                for offset in [-1,0,1]:
                    point = (round(lon+offset*.12*nx/scale,4),round(lat+offset*.12*ny,4))
                    if -180<=point[0]<=180 and -85<=point[1]<=85:
                        points.add(point)
                remaining += spacing
            remaining -= distance
        points.add(tuple(round(v,4) for v in geometry[-1]))
    return sorted(points)[:120],max(30000,spacing*.8)
