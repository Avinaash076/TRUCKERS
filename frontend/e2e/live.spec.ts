import {test,expect} from '@playwright/test'
test('live browser-to-Django-to-provider workflow',async({page})=>{
 test.skip(process.env.LIVE_PROVIDERS!=='1','Opt-in real provider usage')
 await page.goto('/')
 for(const [name,query] of [['Origin','New York'],['Destination','Boston']]){
  await page.getByRole('textbox',{name,exact:true}).fill(query)
  await page.getByRole('button',{name:'Search '+name}).click()
  await expect(page.locator('.search-results button').first()).toBeVisible({timeout:45000})
  await page.locator('.search-results button').first().click()
 }
 await page.getByLabel('Checkpoints',{exact:true}).selectOption('50')
 await page.getByRole('button',{name:'Find safest route'}).click()
 await expect(page.locator('.route-card').first()).toBeVisible({timeout:150000})
 await expect(page.getByRole('slider')).toBeEnabled({timeout:150000})
 await page.getByRole('slider').fill('48')
 await expect(page.locator('.forecast-badge')).toHaveText('+48h')
 await page.locator('.sidebar').evaluate(e=>e.scrollTop=0)
 await page.screenshot({path:'../output/live-browser.png',fullPage:true})
})
