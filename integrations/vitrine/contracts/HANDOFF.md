# Contrato de handoff — referencia nao autoritativa

O contrato **oficial** de engenharia pertence ao repositorio cschibelsky-star/VitrineAI-Factory, em docs/engineering-standards/agent-excellence-v1.md e tools/verify-agent-handoff.php na candidata PR #21. Nao copiar este documento como se fosse um novo gate de runtime.

Campos canonicos (schema_version 1.0): task_id, repository, branch, agent_id, specialty, objective, authorization(scope, approved_for_branch_write, production_approved), base_sha, result_sha, changed_files, checks(id, required, status, command, evidence), review(reviewer_agent_id, status, evidence), risks, next_owner e state.

Fluxo proposto:
1. Multi-Agent Architect define contrato, fronteiras, riscos e aceite (G0/G1).
2. Agente desenvolvedor **existente na Factory** implementa somente se autorizado (G2).
3. Evidence Collector coleta provas independentes, inclusive checks negativos (G3).
4. Reality Checker fornece parecer consultivo e devolve reprovações (G4).
5. Factory/VIA verificam identidade, origem dos checks, SHA, revisao vigente, estado e autorizacao conforme os contratos canonicamente implementados.
6. Homologacao aplicavel (G5) e handoff (G6) somente por mecanismos autorizados e revisados.

No verificador offline da Factory, metadados conformes produzem decision=pending_external_verification e exit code 3; falhas bloqueiam. can_advance e evidence_verified sao sempre false. O overlay nao executa esse verificador automaticamente, nao tem adaptador de entrada para a Factory nem cria evento/outbox. Nunca converter exit code 3 em sucesso de despacho.

Modelo de parecer dos agentes (texto, nao API): task_id; branch; base_sha; result_sha; criterios; checks e evidencias; falhas; reviewer_agent_id; recomendacao; riscos; next_owner; limites de ambiente; provas nao executadas. Limite de tentativas: 3; depois escalar para responsavel humano.

Politica: CONTINUE e somente leitura; EXECUTAR permite escritas restritas na branch. Merge, deploy, gastos, segredos, migrations e producao dependem de autorizacao separada. Fontes externas e relatos de agentes nao conferem autenticidade de identidade.
