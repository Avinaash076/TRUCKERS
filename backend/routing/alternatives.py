"""Bounded, real-road waypoint alternatives when native alternatives are scarce."""
from bisect import bisect_right
from math import cos, radians, hypot, ceil


def waypoint_candidates(route):
    geometry, distances = route["geometry"], route["distances"]
    total = sum(distances)
    if total < 8000 or len(geometry) < 2:
        return []
    cumulative = [0.0]
    for distance in distances:
        cumulative.append(cumulative[-1] + distance)
    offset = max(2000, min(80000, total * .09))
    points = []
    for fraction, side in [(.45, 1), (.55, -1), (.6, 1), (.4, -1)]:
        target = total * fraction
        index = min(bisect_right(cumulative, target)-1, len(distances)-1)
        ratio = (target-cumulative[index])/distances[index] if distances[index] else 0
        lon, lat = [geometry[index][j]+ratio*(geometry[index+1][j]-geometry[index][j]) for j in range(2)]
        a, b = geometry[max(0,index-8)], geometry[min(len(geometry)-1,index+8)]
        scale = max(.2, cos(radians(lat)))
        dx, dy = (b[0]-a[0])*scale, b[1]-a[1]
        length = hypot(dx,dy)
        if not length:
            continue
        point = [round(lon-side*dy/length*offset/111320/scale,6), round(lat+side*dx/length*offset/111320,6)]
        if -180<=point[0]<=180 and -85<=point[1]<=85:
            points.append(point)
    return points


def cells(route):
    occupied = set()
    for a,b in zip(route["geometry"],route["geometry"][1:]):
        steps = max(1,ceil(max(abs(b[0]-a[0]),abs(b[1]-a[1]))/.005))
        for index in range(steps+1):
            fraction = index/steps
            occupied.add((round((a[0]+fraction*(b[0]-a[0]))/.005),round((a[1]+fraction*(b[1]-a[1]))/.005)))
    return occupied


def substantially_distinct(candidate, existing):
    for route in existing:
        occupied = cells(route)
        novel = 0.0
        for a,b,distance in zip(candidate["geometry"],candidate["geometry"][1:],candidate["distances"]):
            x,y = round((a[0]+b[0])/.01),round((a[1]+b[1])/.01)
            if not any((x+dx,y+dy) in occupied for dx in [-1,0,1] for dy in [-1,0,1]):
                novel += distance
        if novel < max(1500,min(15000,route["distance_miles"]*1609.344*.03)):
            return False
    return True


def reasonable(candidate, baseline):
    if candidate["distance_miles"] > baseline["distance_miles"]*1.4 or candidate["duration_seconds"] > baseline["duration_seconds"]*1.5:
        return False
    # Reject meaningful out-and-back excursions to a dead-end waypoint.
    seen, repeated = set(),0.0
    for a,b,distance in zip(candidate["geometry"],candidate["geometry"][1:],candidate["distances"]):
        edge = tuple(sorted((tuple(round(v,5) for v in a),tuple(round(v,5) for v in b))))
        if edge in seen:
            repeated += distance
        seen.add(edge)
    return repeated <= max(500,baseline["distance_miles"]*1609.344*.005)
