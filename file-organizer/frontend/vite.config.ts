import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  server: {
    host: "0.0.0.0", // Permite acesso na sua rede local
    port: 8080,
    // ADICIONE ESTA SEÇÃO DE PROXY
    proxy: {
      // Redireciona todas as requisições de /ws para o backend FastAPI
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true, // Habilita o proxy para WebSockets
      },
      // Redireciona outras requisições de API (como /feed)
      '/feed': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      }
    }
  },
  plugins: [
    react(),
    mode === 'development' &&
    componentTagger(),
  ].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
}));
