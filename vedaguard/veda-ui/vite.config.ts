import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // algosdk / wallet stacks sometimes reference Node's `global`; browsers only have globalThis.
  define: {
    global: 'globalThis',
  },
})
