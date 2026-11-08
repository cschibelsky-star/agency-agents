# Agency Agents — overlay experimental da Vitrine IA Pro

Esta pasta adiciona um conjunto piloto, opt-in e isolado de tres perfis adaptados do Agency Agents. O conteudo original do fork permanece intacto. Esta camada nao substitui a Factory, a VIA, os gates canonicos, o Core nem o Marketing IA.

## Perfis

| Perfil | Fonte original | Papel |
| --- | --- | --- |
| Vitrine Multi-Agent Architect | engineering/engineering-multi-agent-systems-architect.md | Propor contratos e arquitetura sem alterar sistemas |
| Vitrine Evidence Collector | testing/testing-evidence-collector.md | Levantar evidencias reproduziveis sem autodeclarar aprovacao |
| Vitrine Reality Checker | testing/testing-reality-checker.md | Revisao independente e parecer de risco; nao libera agentes |

As tres instrucoes estao em integrations/vitrine/agents/. O manifesto legivel por maquina fica em integrations/vitrine/manifest.json.

## Uso local deliberado

Requisitos: Python 3.11+; nao requer token, API nem servico externo.

- Visualizar destinos sem gravar: python3 integrations/vitrine/tools/install_agents.py --tool claude-code --dest ~/.claude/agents
- Instalar explicitamente em Claude Code: python3 integrations/vitrine/tools/install_agents.py --tool claude-code --dest ~/.claude/agents --apply
- Visualizar destinos para Codex CLI: python3 integrations/vitrine/tools/install_agents.py --tool codex --dest ~/.codex/agents
- Instalar explicitamente no Codex CLI: python3 integrations/vitrine/tools/install_agents.py --tool codex --dest ~/.codex/agents --apply
- Testar localmente: python3 -m unittest discover -s integrations/vitrine/tests -v

O instalador nunca sobrescreve arquivos existentes, nao faz instalacao remota e nao configura ChatGPT via navegador. Para trabalho supervisionado no ChatGPT, seguir integrations/vitrine/AGENTS.md e importar somente os tres perfis no contexto do projeto. Para Claude Code, seguir tambem integrations/vitrine/CLAUDE.md.

## Fronteiras e fonte de verdade

- Factory (cschibelsky-star/VitrineAI-Factory, PR #21): missao canonica, persistencia, runner, autorizacoes e gate de handoff.
- VIA (cschibelsky-star/via, PR #37): supervisor em modo OBSERVER; avalia evidencias, mas nao libera execucao.
- Marketing IA (cschibelsky-star/vitrine-ai-pro, PR #162): limites entre campanha criativa e engenharia.
- Nenhum perfil desta pasta pode alterar o estado da missao, acionar o proximo agente, publicar campanha, executar migracao, alterar producao ou fazer chamadas de IA pagas.
- CONTINUE permite apenas leitura; EXECUTAR autoriza escrita somente no escopo imediato e em branch isolada; merge, deploy, segredos, despesas e producao exigem autorizacao especifica.
- GitHub e fonte de verdade; handoff deve incluir SHA e evidencias verificaveis. Politica e autenticidade nao podem ser definidas pelo proprio agente.

## Estado

Piloto documental e instalador local para Claude/Codex, com testes offline. Nao existe adaptador de runtime com Factory/VIA, worker, MCP ativado, homologacao HML ou certificacao de producao. Gate G0-G6 permanece sob a governanca canonica. Consulte integrations/vitrine/contracts/HANDOFF.md.

## Dependencias de promocao

Revisao independente para SHA vigente, checks obrigatorios, validacao do contrato canonico, homologacao isolada autorizada e posterior autorizacao explicita para integracao no runtime. Os PRs #21/#37/#162 estao em draft na data de elaboracao.
