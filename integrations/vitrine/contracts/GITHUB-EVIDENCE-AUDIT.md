# GitHub PR Evidence Audit — leitura autenticada, sem autorizacao operacional

O script integrations/vitrine/tools/audit_github_pr.py consulta diretamente o GitHub
REST (GET) com GITHUB_TOKEN e compara o SHA atual do PR, o estado do PR, as
revisoes independentes submetidas para esse SHA e os seis workflows obrigatorios.
O workflow tem somente permissoes contents:read, actions:read, pull-requests:read.

Decisao:
- blocked: PR em draft, SHA inconsistente, review atual ausente, workflow
  ausente/falho/pendente ou consulta incompleta;
- pending_via_supervision: todos os checks e um review externo vigente
  encontrados, mas a VIA ainda precisa aplicar a politica server-side.

A auditoria NUNCA devolve can_advance=true, dispatch_allowed=true ou
production_allowed=true, nunca registra um review e nunca habilita o runtime.
O workflow pode ser verde por ter executado a consulta corretamente enquanto
o JSON aponta decision=blocked. Conferir o JSON, nao apenas o icone do job.

Uma resposta autenticada do GitHub comprova apenas o estado dos registros do
GitHub. NAO comprova que o login corresponda ao agente declarado, que os
workflows listados sejam os exigidos pela Factory no servidor ou que a VIA
tenha aprovado uma missao. Esse mapeamento deve ser conferido pelo supervisor.

Limites: somente o PR do mesmo repositorio do job; nenhum token e exibido ou
persistido, nenhum acesso a VPS, filas, bancos, APIs pagas ou producao.
Se houver mais de 100 registros paginados, a consulta e tratada como
incompleta e bloqueada. Nada e mesclado ou implantado.
