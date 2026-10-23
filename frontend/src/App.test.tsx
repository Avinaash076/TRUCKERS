// @vitest-environment jsdom
import React from 'react'
import {describe,it,expect,vi,afterEach} from 'vitest'
import {render,screen,fireEvent,waitFor,cleanup,act} from '@testing-library/react'
import App from './App'
import {api} from './api'
import {duration} from './types'
vi.mock('./api',()=>({api:vi.fn()}))
vi.mock('./MapView',()=>({default:({hour}:{hour:number})=><div data-testid="map-hour">{hour}</div>}))
vi.mock('./PlaceSearch',()=>({default:({label,onChange}:{label:string;onChange:(p:unknown)=>void})=><button type="button" onClick={()=>onChange({label,coordinate:label==='Origin'?[0,0]:[1,1]})}>Select {label}</button>}))
afterEach(()=>{cleanup();vi.resetAllMocks()})
const risk={score:0,label:'Low',reasons:[]}
const route={id:'a',geometry:[[0,0],[1,1]],distance_miles:30,duration_seconds:3600,checkpoints:[{coordinate:[0,0],mile:0,eta:'2026-10-23T10:00:00Z',risk,weather:null},{coordinate:[1,1],mile:30,eta:'2026-10-23T11:00:00Z',risk,weather:null}],risk_miles:{Low:30,Moderate:0,High:0,Severe:0,'No Travel':0},unknown_miles:0,average_risk:0,eligible:true}
const assessment={weather_provider:{id:"weatherapi",name:"WeatherAPI.com",url:"https://www.weatherapi.com/",forecast_days:3,notice:""},assessment_status:'complete',routes:[route],recommended_id:'a',warnings:[],assessed_at:'2026-10-23T10:00:00Z'}
const preview={...assessment,assessment_status:'pending',recommended_id:null}
const corridor={anchor:'2026-10-23T10:00:00Z',radius_m:30000,samples:[{coordinate:[0,0],hours:Array.from({length:49},(_,h)=>({weather:{wind_mph:h},risk:{...risk,score:h===48?3:0}}))}]}
function mockResponses(overrides:Record<string,unknown>={}){
 vi.mocked(api).mockImplementation((path)=>Promise.resolve(({ 'routes/':preview,'assess/':assessment,'corridor/':corridor,...overrides })[path] as never))
}
async function submit(){fireEvent.click(screen.getByText('Select Origin'));fireEvent.click(screen.getByText('Select Destination'));fireEvent.click(screen.getByText('Find safest route'))}

describe('trip workflow',()=>{
 it('rounds duration over an hour without displaying 60 minutes',()=>{expect(duration(14399)).toBe('4h 0m')})
 it('requires selected locations',()=>{render(<App/>);expect((screen.getByText('Find safest route').closest('button') as HTMLButtonElement).disabled).toBe(true)})
 it('shows actionable API failure and permits retry',async()=>{
  vi.mocked(api).mockRejectedValue(new Error('Routing unavailable'));render(<App/>);await submit()
  await waitFor(()=>expect(screen.getByRole('alert').textContent).toContain('Routing unavailable'))
  expect((screen.getByText('Find safest route').closest('button') as HTMLButtonElement).disabled).toBe(false)
 })
 it('changes corridor hour and puts arrival time in the route card',async()=>{
  mockResponses();const {container}=render(<App/>);await submit()
  const slider=screen.getByRole('slider')
  await waitFor(()=>expect((slider as HTMLInputElement).disabled).toBe(false))
  for(const hour of [0,24,48]){fireEvent.change(slider,{target:{value:String(hour)}});expect(screen.getByTestId('map-hour').textContent).toBe(String(hour))}
  expect(screen.getByText('Recommended')).toBeTruthy()
  expect(screen.getByRole('link',{name:'WeatherAPI.com'})).toBeTruthy()
  expect(container.querySelector('.route-card time')?.getAttribute('datetime')).toBe('2026-10-23T11:00:00Z')
  expect(container.querySelector('.journey-strip')).toBeNull()
  expect(screen.getByText('Route B')).toBeTruthy()
  expect(screen.getByText('Route C')).toBeTruthy()
 })
 it('shows ETAs while weather is pending and does not claim zero risk or recommend',async()=>{
  let finish!:(value:unknown)=>void
  const pending=new Promise(resolve=>{finish=resolve})
  vi.mocked(api).mockImplementation((path)=>path==='assess/'?pending as never:Promise.resolve((path==='routes/'?preview:corridor) as never))
  const {container}=render(<App/>);await submit()
  await waitFor(()=>expect(container.querySelector('.route-arrival time')).toBeTruthy())
  expect(screen.queryByText('Recommended')).toBeNull()
  expect(screen.queryByText(/0.0 severe mi/)).toBeNull()
  expect(screen.getByText('Assessing checkpoint weather...')).toBeTruthy()
  await act(async()=>{finish(assessment)})
  expect(screen.getByText('Recommended')).toBeTruthy()
 })
 it('unlocks planning after assessment without waiting for the corridor',async()=>{
  let finish!:(value:unknown)=>void
  const pending=new Promise(resolve=>{finish=resolve})
  vi.mocked(api).mockImplementation((path)=>path==='corridor/'?pending as never:Promise.resolve((path==='routes/'?preview:assessment) as never))
  render(<App/>);await submit()
  await waitFor(()=>expect((screen.getByText('Find safest route').closest('button') as HTMLButtonElement).disabled).toBe(false))
  expect((screen.getByRole('slider') as HTMLInputElement).disabled).toBe(true)
  await act(async()=>{finish(corridor)})
  expect((screen.getByRole('slider') as HTMLInputElement).disabled).toBe(false)
 })
 it('preserves a route selection made before assessment finishes',async()=>{
  let finish!:(value:unknown)=>void
  const pending=new Promise(resolve=>{finish=resolve})
  const routes=[route,{...route,id:'b'}]
  vi.mocked(api).mockImplementation((path)=>path==='assess/'?pending as never:Promise.resolve((path==='routes/'?{...preview,routes}:corridor) as never))
  render(<App/>);await submit()
  const alternative=await screen.findByRole('button',{name:/Route B/})
  fireEvent.click(alternative)
  await act(async()=>{finish({...assessment,routes})})
  expect(screen.getByRole('button',{name:/Route B/}).getAttribute('aria-pressed')).toBe('true')
 })
})
