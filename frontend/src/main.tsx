// PATCH DE COMPATIBILIDADE REACT 19 + ANT DESIGN V5
// Elimina warnings de compatibilidade e habilita message/modal/notification static methods
// Documentação: https://ant.design/docs/react/v5-for-19/
import '@ant-design/v5-patch-for-react-19';

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// StrictMode ativo para detectar erros em desenvolvimento
// Nota: Causa duplicação de requisições/logs em dev (comportamento normal do React 18+)
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
