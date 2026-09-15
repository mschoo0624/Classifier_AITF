import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import tailwindcss from '@tailwindcss/vite'

// 지금은 public/data.json 을 정적으로 읽습니다.
// 실제 백엔드가 준비되면 아래 proxy 를 켜고, src/api.ts 의
// DATA_SOURCE 를 'api' 로 바꾸면 됩니다. 화면 코드는 안 건드립니다.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8002',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
