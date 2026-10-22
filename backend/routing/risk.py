LABELS = ["Low", "Moderate", "High", "Severe", "No Travel"]

def classify(wind, rain, snow, load):
    wind_risk = next((i for i,t in enumerate([25,35,45,55]) if wind < t), 4)
    rain_risk = 0 if rain < .10 else 1 if rain < .25 else 2 if rain < .50 else 3 if rain <= 1 else 4
    snow_risk = 0 if snow < .5 else 1 if snow < 1 else 2 if snow < 2 else 3 if snow <= 3 else 4
    load_risk = 4 if wind >= 55 or (45 <= wind < 55 and load > 30000) else 3 if 35 <= wind < 45 and load > 40000 else 0
    score = max(wind_risk, rain_risk, snow_risk, load_risk)
    reasons = [f"{name}: {LABELS[value]}" for name,value in [("Wind",wind_risk),("Rain",rain_risk),("Snow",snow_risk),("Load / wind",load_risk)] if value > 0]
    return {"score":score, "label":LABELS[score], "reasons":reasons or ["All variables below risk thresholds"]}

def summarize(route):
    miles = dict.fromkeys(LABELS, 0.0)
    unknown = 0.0
    for a,b in zip(route["checkpoints"],route["checkpoints"][1:]):
        distance = b["mile"]-a["mile"]
        if a["risk"] is None or b["risk"] is None:
            unknown += distance
        else:
            miles[LABELS[max(a["risk"]["score"],b["risk"]["score"])]] += distance
    total = route["distance_miles"]
    route["risk_miles"] = miles
    route["unknown_miles"] = unknown
    route["average_risk"] = sum(i*miles[label] for i,label in enumerate(LABELS))/total if not unknown and total else None
    route["eligible"] = unknown == 0 and miles["No Travel"] == 0 and all(c["risk"] is not None and c["risk"]["score"] < 4 for c in route["checkpoints"])

def recommend(routes):
    eligible = sorted((r for r in routes if r["eligible"]), key=lambda r:(r["risk_miles"]["Severe"],r["risk_miles"]["High"],r["average_risk"],r["duration_seconds"],r["id"]))
    for rank, route in enumerate(eligible,1):
        route["rank"] = rank
    return eligible[0]["id"] if eligible else None
