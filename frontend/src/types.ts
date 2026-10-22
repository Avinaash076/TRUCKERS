export type Point = [number,number]
export type Place = {label:string;coordinate:Point}
export type Risk = {score:number;label:string;reasons:string[]}
export type Weather = {wind_mph:number;rain_in_hr:number;snow_in_hr:number;time:string}
export type Checkpoint = {coordinate:Point;mile:number;eta:string;weather:Weather|null;risk:Risk|null}
export type Route = {id:string;geometry:Point[];distance_miles:number;duration_seconds:number;checkpoints:Checkpoint[];risk_miles:Record<string,number>;unknown_miles:number;average_risk:number|null;eligible:boolean;rank?:number}
export type WeatherProvider = {id:string;name:string;url:string;forecast_days:number;notice:string}
export type Assessment = {weather_provider?:WeatherProvider;routes:Route[];recommended_id:string|null;warnings:string[];assessed_at:string;ranking_rule:string}
export type Corridor = {weather_provider?:WeatherProvider;anchor:string;radius_m:number;samples:{coordinate:Point;hours:({weather:Weather;risk:Risk}|null)[]}[]}
export const colors = ['#278268','#d2ad31','#e58b36','#ce5451','#793b67']
export const labels = ['Low','Moderate','High','Severe','No Travel']
export const routeColors = ['#256caa','#7a5eb4','#af7633']
export const time = (value:string) => new Date(value).toLocaleString(undefined,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit',timeZoneName:'short'})
export const duration = (seconds:number) => {const minutes=Math.round(seconds/60);return `${Math.floor(minutes/60)}h ${minutes%60}m`}
