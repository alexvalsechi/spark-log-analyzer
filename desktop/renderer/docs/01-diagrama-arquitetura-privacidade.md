# 1. Diagrama de Arquitetura de Privacidade

## Fluxo real de dados (código atual)

```mermaid
flowchart TD
    U[Usuario no Electron UI\nrenderer/index.html] --> F[Seleciona ZIP e .py opcionais\nFormData]
    F --> R1[POST /api/upload\nbackend/api/routes.py]
    R1 --> J[(Memoria do processo\n_jobs[job_id])]
    R1 --> C[Celery task\nprocess_reduced_task]
    C --> S[JobService.process_reduced]
    S --> L[LLMAnalyzer.analyze]
    L --> E1[OpenAI API]
    L --> E2[Anthropic API]
    L --> E3[Google Gemini API]
    C --> J
    U --> P[Polling GET /api/status/{job_id}\n1.5s]
    P --> J
    J --> U2[Renderizacao no UI\nKPI + tabela + analise]
    U2 --> D[Download GET /api/download/{job_id}/{md|json}]

    subgraph Observado no codigo, mas fora do fluxo do renderer atual
      I1[Electron main.js IPC\nreduce-zip-locally]
      I2[desktop/scripts/reduce_log.py\nLogReducer local]
      I3[POST /api/upload-reduced]
      I1 --> I2 --> I3
    end
```

## Etapas e implicacoes de privacidade

- Entrada de dados:
  - O frontend em `desktop/renderer/index.html` monta `FormData` com `log_zip`, `pyspark_files[]`, `compact`, `language`, e credenciais (`provider/user_id` ou `llm_provider/api_key`).
  - Chamada atual: `fetch(apiUrl('/api/upload'))`.

- Onde o log e processado:
  - No fluxo efetivo do renderer atual, o processamento e remoto (backend).
  - Existe um fluxo de reducao local implementado em `desktop/main.js` + `desktop/scripts/reduce_log.py`, mas ele nao esta conectado ao JavaScript do renderer no arquivo atual.

- O que e extraido/reduzido antes de envio externo:
  - No fluxo remoto (`/api/upload`), o ZIP e enviado para backend; a reducao ocorre no servidor via `backend/services/log_reducer.py`.
  - Antes de enviar ao provedor LLM, o backend monta prompt com:
    - `reduced_report[:6000]`
    - para cada `.py`, conteudo truncado para `[:2000]`.
  - Isso ocorre em `backend/services/llm_analyzer.py`.

- Endpoints externos chamados e payload:
  - OpenAI (`chat.completions.create`), Anthropic (`messages.create`) e Gemini (`generate_content`) em `backend/adapters/llm_adapters.py`.
  - Todos recebem um `prompt` textual unico contendo relatorio reduzido e, opcionalmente, trechos de `.py`.

- O que retorna ao usuario e onde aparece:
  - Backend retorna status em `/api/status/{job_id}` e resultado com `reduced_report` e `llm_analysis` quando concluido.
  - O renderer exibe em `renderResults()`:
    - cartoes KPI
    - tabela de stages
    - secao de analise AI
    - links de download (`/api/download/{job_id}/md|json`).

- O que nao e armazenado de forma duravel:
  - Nao ha banco relacional/documental de historico no codigo atual.
  - `_jobs` e memoria do processo em `backend/api/routes.py`.
  - Arquivos de download sao temporarios e removidos no `finally` do endpoint de download.
  - No desktop, o arquivo temporario da reducao local e apagado apos leitura em `desktop/main.js`.

- O que e armazenado:
  - Tokens OAuth em Redis (chaves `oauth_token:{user_id}:{provider}`) via `backend/auth.py`.
  - Historico visual no frontend em `localStorage` (`sparkui_history`) no renderer.

## Lacunas explicitas no repositorio

- O backend exibido em `backend/api/routes.py` implementa `/upload-reduced`, nao implementa `/upload`.
- O renderer chama `/api/upload`.
- Portanto, no estado atual do codigo, ha divergencia entre fluxo de UI e rotas de backend, o que impacta o caminho de privacidade em execucao.