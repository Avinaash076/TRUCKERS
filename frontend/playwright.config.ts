import {defineConfig} from '@playwright/test'
export default defineConfig({testDir:'./e2e',webServer:{command:'npm run dev -- --port 5173 --strictPort',url:'http://127.0.0.1:5173',reuseExistingServer:true,timeout:30000},timeout:180000,use:{baseURL:'http://127.0.0.1:5173',channel:'msedge',headless:true,screenshot:'only-on-failure'},outputDir:'../output/playwright',reporter:'list'})
