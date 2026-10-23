import { useEffect,useRef,useState,useMemo,memo } from 'react'
import L from 'leaflet'
import { MapContainer,TileLayer,Polyline,CircleMarker,Popup,ZoomControl,useMap } from 'react-leaflet'
import type { Assessment,Checkpoint,Corridor,Point } from './types'
import { colors,routeColors,time } from './types'
const latlng=(p:Point):[number,number]=>[p[1],p[0]]
function Fit({data}:{data:Assessment|null}){
 const map=useMap()
 const routeKey=data?.routes.map(r=>r.id).join(",")
 useEffect(()=>{if(data?.routes.length)map.fitBounds(L.latLngBounds(data.routes.flatMap(r=>r.geometry.map(latlng))),{paddingTopLeft:[24,120],paddingBottomRight:[24,180]})},[map,routeKey])
 return null
}
function Heat({data,hour,visible}:{data:Corridor|null;hour:number;visible:boolean}){
 const map=useMap(),state=useRef({data,hour,visible})
 state.current={data,hour,visible}
 const redraw=useRef<()=>void>(()=>{})
 useEffect(()=>{
  let pane=map.getPane('weather')
  if(!pane){pane=map.createPane('weather');pane.style.zIndex='350';pane.style.pointerEvents='none'}
  const canvas=L.DomUtil.create('canvas','weather-canvas',pane)
  const draw=()=>{
   const {data,hour,visible}=state.current,size=map.getSize(),ratio=window.devicePixelRatio||1
   canvas.width=size.x*ratio;canvas.height=size.y*ratio;canvas.style.width=size.x+'px';canvas.style.height=size.y+'px'
   L.DomUtil.setPosition(canvas,map.containerPointToLayerPoint([0,0]))
   const ctx=canvas.getContext('2d')!;ctx.scale(ratio,ratio)
   if(!data||!visible)return
   for(const sample of data.samples){
    const value=sample.hours[hour],p=map.latLngToContainerPoint(latlng(sample.coordinate))
    const radius=data.radius_m/(40075016.686*Math.cos(sample.coordinate[1]*Math.PI/180)/(256*2**map.getZoom()))
    const color=value?colors[value.risk.score]:'#87939b'
    const gradient=ctx.createRadialGradient(p.x,p.y,0,p.x,p.y,radius)
    gradient.addColorStop(0,color+'65');gradient.addColorStop(.5,color+'30');gradient.addColorStop(1,color+'00')
    ctx.fillStyle=gradient;ctx.fillRect(p.x-radius,p.y-radius,radius*2,radius*2)
   }
  }
  redraw.current=draw;map.on('moveend zoomend resize',draw);draw()
  return ()=>{map.off('moveend zoomend resize',draw);canvas.remove()}
 },[map])
 useEffect(()=>{redraw.current()},[data,hour,visible])
 return null
}
const RoadLayers = memo(function RoadLayers({data,selected,onSelect,onCheckpoint}:{data:Assessment|null;selected:string;onSelect:(id:string)=>void;onCheckpoint:(c:Checkpoint)=>void}){
 const roads=useMemo(()=>data?.routes.map(r=>({...r,positions:r.geometry.map(latlng)}))||[],[data?.routes])
 return <>  {roads.map((r,i)=><Polyline key={r.id} positions={r.positions} pathOptions={{color:routeColors[i],weight:selected===r.id?6:3,opacity:selected===r.id?1:.55}} eventHandlers={{click:()=>onSelect(r.id)}}/>)}
  {data?.routes.find(r=>r.id===selected)?.checkpoints.map((c,i)=><CircleMarker key={i} center={latlng(c.coordinate)} radius={i===0?7:5} pathOptions={{color:'#fff',weight:2,fillColor:c.risk?colors[c.risk.score]:'#87939b',fillOpacity:1}} eventHandlers={{click:()=>onCheckpoint(c)}}><Popup><strong>{c.mile.toFixed(1)} mi · {c.risk?.label||'Unknown'}</strong><br/>{time(c.eta)}<br/>{c.weather?c.weather.wind_mph.toFixed(1)+' mph wind':'Weather unavailable'}</Popup></CircleMarker>)}</>
})
export default function MapView({data,selected,onSelect,onCheckpoint,corridor,hour,showHeat}:{data:Assessment|null;selected:string;onSelect:(id:string)=>void;onCheckpoint:(c:Checkpoint)=>void;corridor:Corridor|null;hour:number;showHeat:boolean}){
 const [tileFailed,setTileFailed]=useState(false)
 return <><MapContainer center={[38.5,-96]} zoom={4} zoomControl={false} preferCanvas className="route-map">
  <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" eventHandlers={{tileerror:()=>setTileFailed(true),tileload:()=>setTileFailed(false)}}/>
  <ZoomControl position="topright"/>
  <Fit data={data}/><Heat data={corridor} hour={hour} visible={showHeat}/>
  <RoadLayers data={data} selected={selected} onSelect={onSelect} onCheckpoint={onCheckpoint}/>
 </MapContainer>{tileFailed&&<div className="tile-warning" role="status">Some map tiles are unavailable. Routes and weather remain visible.</div>}</>
}
