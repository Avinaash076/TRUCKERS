import { useState } from 'react'
import { Search, MapPin } from 'lucide-react'
import { api } from './api'
import type { Place } from './types'
export default function PlaceSearch({label,value,onChange}:{label:string;value:Place|null;onChange:(place:Place|null)=>void}){
 const [query,setQuery]=useState(value?.label||'')
 const [results,setResults]=useState<Place[]>([])
 const [busy,setBusy]=useState(false)
 const [error,setError]=useState('')
 async function search(){
  if(query.trim().length<2)return
  setBusy(true);setError('');setResults([])
  try { const data=await api<{results:Place[]}>('geocode/?q='+encodeURIComponent(query));setResults(data.results);if(!data.results.length)setError('No locations found. Try a city and state.') }
  catch(e){setError((e as Error).message)}finally{setBusy(false)}
 }
 return <div className="place-field"><label>{label}<div className="search-input"><MapPin size={16}/><input aria-label={label} value={query} placeholder="City, state or address" onChange={e=>{setQuery(e.target.value);onChange(null);setResults([])}} onKeyDown={e=>{if(e.key==='Enter'){e.preventDefault();void search()}}}/><button type="button" aria-label={'Search '+label} disabled={busy||query.trim().length<2} onClick={()=>void search()}>{busy?<span className="spinner"/>:<Search size={16}/>}</button></div></label>{value&&<span className="verified">Location selected</span>}{error&&<p className="field-error" role="alert">{error}</p>}{results.length>0&&<ul className="search-results">{results.map(place=><li key={place.label}><button type="button" onClick={()=>{onChange(place);setQuery(place.label);setResults([])}}>{place.label}</button></li>)}</ul>}</div>
}
