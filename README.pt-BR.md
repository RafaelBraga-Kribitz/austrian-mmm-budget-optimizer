# MMM austríaco e otimizador de orçamento

[🇧🇷 PT-BR](README.pt-BR.md) · [🇬🇧 EN-UK](README.md) · [🇦🇹 DE-AT](README.de-AT.md)

## Resumo

Este repositório demonstra um modelo bayesiano de marketing mix (MMM) e uma regra para redistribuir orçamento de mídia. A estrutura foi pensada para um anunciante austríaco, mas **nenhum dado de cliente austríaco foi usado**. O modelo é validado com dados artificiais cujo resultado verdadeiro é conhecido e demonstrado com uma base pública de exemplo.

Na base pública, a recomendação é reduzir em 20% o investimento em mídia out-of-home e aumentar em 50% TV e Facebook, mantendo o orçamento total. O ganho mediano estimado é de 15,1% sobre a contribuição atual de mídia; o percentil 10 é 8,8%, e nenhum dos 500 sorteios posteriores apresenta perda. Os valores monetários estão nas unidades da base de demonstração, **não em euros**.

O modelo informa a contribuição incremental por canal com intervalos de 90%, avalia a divergência em relação aos números reportados pelas plataformas e aplica uma regra de ponto de equilíbrio. O investimento só é deslocado para um canal se o limite inferior do retorno marginal sobre o investimento em publicidade (ROAS) superar o ponto de equilíbrio.

## O que o projeto demonstra

- MMM bayesiano com curvas de resposta e incerteza explícita.
- Validação em dados artificiais com verdade conhecida.
- Recomendação de orçamento condicionada a uma regra de equilíbrio, em vez de ordenar canais apenas pela mediana.
- Controles para o calendário de feriados austríacos e granularidade semanal.

## Limites essenciais

A demonstração pública não é um caso comercial austríaco e não deve ser interpretada como resultado em euros. As recomendações dependem de hipóteses sobre margem e limites de movimentação. Uma aplicação real requer dados próprios do anunciante e validação local.

## Explorar

Consulte o [README completo em inglês](README.md) para resultados, tabelas, dashboards, metodologia e instruções de execução. Veja também a [avaliação econômica](docs/economic-evaluation.md).

[Repositório](https://github.com/RafaelBraga-Kribitz/austrian-mmm-budget-optimizer)
