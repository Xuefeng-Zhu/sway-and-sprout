import {defineConfig} from 'vite';

// Development only. Both local routes target the fixed loopback sidecar.
export default defineConfig({server:{host:'127.0.0.1',port:4173,strictPort:true,
  proxy:{
    '/motion/events':{target:'http://127.0.0.1:8765',changeOrigin:true,timeout:1600,proxyTimeout:1400},
    '/motion/preview':{target:'http://127.0.0.1:8765',changeOrigin:true,timeout:1600,proxyTimeout:1400},
  }}});
