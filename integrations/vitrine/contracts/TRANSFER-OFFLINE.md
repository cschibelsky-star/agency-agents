# Auditoria de transferencias offline (Agency Agents / Factory / VIA)

Este linter valida apenas consistencia entre alegacoes declaradas em tres arquivos JSON locais. Nao autentica GitHub, revisor ou identidade, nao executa testes, nao integra runtime, nao libera agentes e nao substitui o gate canonico da Factory.

Uso: python3 integrations/vitrine/tools/validate_transfer.py --handoff handoff.json --stages stages.json --snapshot snapshot.json

Handoff segue o contrato Factory v1.0. O stages contem tres itens ordenados: architecture (SHA base), quality_evidence (SHA resultado) e independent_review (SHA resultado); cada item inclui role, agent_id, task_id, repository, branch, sha e evidence. O snapshot (fixture fornecida pelo operador, sem autenticacao) declara task_id, repository, branch, base_sha, result_sha, author_agent_id, author_login, checks [{id,sha,conclusion,source,run_id,run_url}] e review {reviewer_agent_id,reviewer_login,sha,status,evidence}.

O linter recusa checks ausentes ou falhos, divergencia de SHA e origem declarada, auto-revisao, identidade declarada incorreta, evidencia ausente ou divergente, branch principal e campos privilegiados. Mesmo se tudo coincidir, devolve pending_external_verification, com can_advance=false, dispatch_allowed=false, evidence_verified=false, production_allowed=false e authenticated_externally=false. Codigos de saida: 1 blocked; 2 entrada invalida; 3 metadata consistente pendente da VIA; nunca retorna 0.

Observacao: um snapshot local pode ser fabricado. Os testes usam fixtures artificiais e nao comprovam revisao, CI, execucao ou autenticidade real. Factory #21 e VIA #37 permanecem autoritativas; autenticar tokens de politica, revisar identidades e homologar exige outro escopo e autorizacao.


## Comparacao com o gate PHP real da Factory

O workflow do overlay tambem faz checkout **somente leitura** da Factory no commit imutavel `81131c2b1546b4d0d9d16996b9d2c1fbca9aefa3` e executa o verificador PHP `tools/verify-agent-handoff.php` em um runner GitHub isolado, usando apenas 13 fixtures sinteticas do script `integrations/vitrine/tools/check_factory_contract.py`. O teste espera exit 1 para rascunhos e corrupcoes, e exit 3 para um conjunto de metadados artificialmente conforme. Sempre exige `can_advance=false` e `evidence_verified=false`. Nenhuma credencial da Factory, banco, HML ou API e acessada.

**Importante:** esta compatibilidade com o gate PHP e apenas prova do contrato estatico. Nao autentica reviews, CI, identidades nem garante validade de uma politica de servidor. A integracao executora real nao esta implementada; o modo VIA OBSERVER permanece bloqueado. Um novo SHA da Factory requer nova revisao e nova fixacao explicita, sem atualizacao automatica.
