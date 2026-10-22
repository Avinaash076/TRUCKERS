from bisect import bisect_right
from datetime import timedelta
from math import asin,cos,radians,sin,sqrt
MILE = 1609.344

def haversine(a,b):
    lon1,lat1,lon2,lat2 = map(radians,[*a,*b])
    return 6371008.8*2*asin(min(1,sqrt(sin((lat2-lat1)/2)**2+cos(lat1)*cos(lat2)*sin((lon2-lon1)/2)**2)))

def checkpoints(geometry,distances,durations,interval,departure):
    if len(distances) != len(geometry)-1 or len(durations) != len(distances) or not distances:
        raise ValueError("Route annotations do not match geometry")
    cumulative,elapsed = [0.0],[0.0]
    for distance,duration in zip(distances,durations):
        cumulative.append(cumulative[-1]+distance)
        elapsed.append(elapsed[-1]+duration)
    total = cumulative[-1]
    targets = [i*interval*MILE for i in range(int(total/(interval*MILE))+1)]
    if total-targets[-1] > .01:
        targets.append(total)
    result = []
    for target in targets:
        i = min(bisect_right(cumulative,target)-1,len(distances)-1)
        fraction = (target-cumulative[i])/distances[i] if distances[i] else 0
        point = [geometry[i][j]+fraction*(geometry[i+1][j]-geometry[i][j]) for j in range(2)]
        seconds = elapsed[i]+fraction*durations[i]
        result.append({"coordinate":point,"mile":target/MILE,"eta":(departure+timedelta(seconds=seconds)).isoformat(),"weather":None,"risk":None})
    return result
