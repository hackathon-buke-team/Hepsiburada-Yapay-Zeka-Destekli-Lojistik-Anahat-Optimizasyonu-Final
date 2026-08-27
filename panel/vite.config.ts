import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { viteSingleFile } from 'vite-plugin-singlefile'

/* İki hedef:
   - `vite build`              -> dist/  (Vercel; normal çok dosyalı çıktı)
   - `vite build --mode tek`   -> dist-tek/index.html  (masaüstü .exe içine gömülür)
   Panonun tamamı çevrimdışı çalışır: dış CDN, font ya da harita servisi yoktur. */
export default defineConfig(({ mode }) => {
  const single = mode === 'tek'
  return {
    plugins: [react(), ...(single ? [viteSingleFile()] : [])],
    base: './',
    build: {
      outDir: single ? 'dist-tek' : 'dist',
      emptyOutDir: true,
      target: 'es2020',
      chunkSizeWarningLimit: 1400,
      assetsInlineLimit: single ? 100_000_000 : 4096,
    },
    server: { port: 5178, strictPort: false },
  }
})
