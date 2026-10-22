import {test,expect} from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'
test('recorded live provider data renders real geometries and a changing forecast',async({page})=>{
 const output=path.resolve('..','output')
 const assessment=JSON.parse(fs.readFileSync(path.join(output,'live-assessment.json'),'utf8'))
 const corridor=JSON.parse(fs.readFileSync(path.join(output,'live-corridor.json'),'utf8'))
 const journey=JSON.parse(fs.readFileSync(path.join(output,'live-journey.json'),'utf8'))
 const errors:string[]=[]
 page.on('pageerror',e=>errors.push(e.message))
 // Only test transport is recorded; the application never falls back to fixtures.
 await page.route('**/api/v1/geocode/**',r=>r.fulfill({json:{results:[r.request().url().includes('Origin')?journey.origin:journey.destination]}}))
 await page.route('**/api/v1/assess/',r=>r.fulfill({json:assessment}))
 await page.route('**/api/v1/corridor/',r=>r.fulfill({json:corridor}))
 await page.goto('/')
 await expect(page.getByRole('heading',{name:'A clearer road ahead.'})).toBeVisible()
 await expect.poll(()=>page.locator('.leaflet-tile-loaded').count()).toBeGreaterThan(0)
 await page.screenshot({path:path.join(output,'desktop-empty.png'),fullPage:true})
 for(const name of ['Origin','Destination']){
  await page.getByRole('textbox',{name,exact:true}).fill(name)
  await page.getByRole('button',{name:'Search '+name}).click()
  await page.getByRole('button',{name:name==='Origin'?journey.origin.label:journey.destination.label,exact:true}).click()
 }
 await page.getByRole('button',{name:'Find safest route'}).click()
 await page.getByRole('button',{name:/Route A/}).scrollIntoViewIfNeeded()
 await expect(page.getByRole('button',{name:/Route A/})).toBeVisible()
 await expect(page.getByRole('button',{name:/Route B/})).toBeVisible()
 if(assessment.routes.length===3)await expect(page.getByRole('button',{name:/Route C/})).toBeVisible();else await expect(page.locator('.unavailable').filter({hasText:'Route C'})).toBeVisible()
 await expect(page.getByRole('slider')).toBeEnabled()
 for(const hour of [0,24,48]){
  await page.getByRole('slider').fill(String(hour))
  await expect(page.locator('.forecast-badge')).toHaveText('+'+hour+'h')
  await page.screenshot({path:path.join(output,'desktop-forecast-'+hour+'.png'),fullPage:true})
 }
 await expect(page.locator('.leaflet-overlay-pane canvas').first()).toBeVisible()
 await page.locator('.checkpoint-list summary').click()
 await page.locator('.checkpoint-list button').first().click()
 await expect(page.locator('.checkpoint-panel')).toBeVisible()
 await page.getByRole('button',{name:'Close checkpoint'}).click()
 await page.getByRole('button',{name:'Weather layer'}).click()
 await expect(page.getByRole('button',{name:'Weather layer'})).toHaveAttribute('aria-pressed','false')
 await page.getByRole('button',{name:/Route B/}).click()
 await expect(page.getByRole('button',{name:/Route B/})).toHaveClass(/selected/)
 await page.setViewportSize({width:390,height:844})
 await page.screenshot({path:path.join(output,'mobile-trip.png'),fullPage:true})
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true)
 expect(errors).toEqual([])
})
