const base = (import.meta.env.VITE_API_URL || '').replace(/\/$/,'')
export async function api<T>(path:string,body?:unknown):Promise<T> {
  const response = await fetch(base+'/api/v1/'+path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined})
  const data = await response.json().catch(()=>({error:'The server returned an unreadable response.'}))
  if(!response.ok) throw new Error(data.error+(data.fields?' '+JSON.stringify(data.fields):''))
  return data
}
