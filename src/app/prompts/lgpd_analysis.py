from __future__ import annotations


class PromptTemplates:
    """Constantes de prompts para análise de LGPD e compliance."""

    ANALYZE_SCHEMA_COMPLIANCE = """IDIOMA OBRIGATÓRIO: PORTUGUÊS DO BRASIL (pt-BR). Não responda em inglês ou em qualquer outro idioma, mesmo que o documento analisado esteja em inglês.

Você é um especialista em LGPD (Lei Geral de Proteção de Dados Pessoais).

Sua tarefa é analisar o SCHEMA/DOCUMENTO de banco de dados em relação aos requisitos da Lei Geral de Proteção de Dados Pessoais.

===== LEI GERAL DE PROTEÇÃO DE DADOS =====
{lgpd_context}

===== SCHEMA/DOCUMENTO A ANALISAR =====
{document_content}

===== ANÁLISE REQUERIDA =====
Forneça uma análise objetiva com os seguintes itens:
1. Tabelas, campos, relacionamentos e dados pessoais identificados
2. Pontos corretos
3. Pontos fora da lei
4. Artigos da LGPD relevantes
5. Riscos e obrigações que faltam
6. Recomendações de adequação

Use linguagem técnica, formal e estruturada. Destaque explicitamente os itens de conformidade e os itens não conformes.

IMPORTANTE: responda integralmente em português do Brasil (pt-BR), independentemente do idioma do documento analisado. Nunca responda em inglês."""

    ANALYZE_TERMS_COMPLIANCE = """IDIOMA OBRIGATÓRIO: PORTUGUÊS DO BRASIL (pt-BR). Não responda em inglês ou em qualquer outro idioma, mesmo que o termo analisado esteja em inglês.

Você é um especialista em LGPD e compliance em proteção de dados.

Sua tarefa é analisar o TERMO DE COMPROMISSO em relação aos requisitos da Lei Geral de Proteção de Dados Pessoais.

===== LEI GERAL DE PROTEÇÃO DE DADOS =====
{lgpd_context}

===== TERMO DE COMPROMISSO A ANALISAR =====
{document_content}

===== ANÁLISE REQUERIDA =====
Avalie os pontos abaixo:
1. Partes interessadas (Controlador, Operador, Titular)
2. Pontos corretos do termo
3. Pontos fora da lei
4. Artigos da LGPD aplicáveis
5. Gaps, riscos e obrigações pendentes
6. Recomendações de adequação

Estruture a resposta de forma clara, técnica e objetiva.

IMPORTANTE: responda integralmente em português do Brasil (pt-BR), independentemente do idioma do documento analisado. Nunca responda em inglês."""

    GENERATE_COMPLIANCE_REPORT = """IDIOMA OBRIGATÓRIO: PORTUGUÊS DO BRASIL (pt-BR). Não responda em inglês ou em qualquer outro idioma, mesmo que o documento original ou a análise anterior estejam em inglês.

Você é um especialista em LGPD e compliance em proteção de dados.

Sua tarefa é gerar um RELATÓRIO EXECUTIVO DE CONFORMIDADE com base no schema/termo comparado à LGPD.

===== LEI GERAL DE PROTEÇÃO DE DADOS =====
{lgpd_context}

===== DOCUMENTO ORIGINAL =====
{document_content}

===== ANÁLISE ANTERIOR =====
{previous_analysis}

===== RELATÓRIO REQUERIDO =====
Gere o relatório em markdown com as seções abaixo, sem omitir nenhum item:

## 1. Resumo executivo
- Visão geral do documento
- Nível de conformidade geral (Alto/Médio/Baixo)
- Observação geral sobre o contexto

## 2. Pontos corretos
- Elementos que atendem à LGPD
- Tabelas/campos/termos que estão apropriados
- Evidências de boa prática

## 3. Pontos fora da lei
- Elementos incompatíveis com a LGPD
- Riscos legais ou de privacidade
- Artigos da lei violados ou ameaçados

## 4. Artigos da LGPD aplicáveis
- Lista dos artigos relevantes
- Explicação breve da aplicação

## 5. Obrigações e riscos
- Obrigações do Controlador
- Obrigações do Operador (se aplicável)
- Riscos de segurança e impacto potencial

## 6. Recomendações
- Ações corretivas prioritárias
- Prazo sugerido
- Responsáveis e prioridades

## 7. Conclusão
- Síntese final
- Próximos passos

Use linguagem formal, objetiva e pronta para ser salvo em banco de dados como relatório de compliance.

IMPORTANTE: escreva o relatório inteiro em português do Brasil (pt-BR), independentemente do idioma do documento original ou da análise anterior. Nunca responda em inglês."""

    ANALYZE_SCHEMA_TERMS_STRUCTURED = """IDIOMA OBRIGATÓRIO: PORTUGUÊS DO BRASIL (pt-BR). Não responda em inglês ou em qualquer outro idioma, mesmo que o schema ou o termo de compromisso estejam em inglês.

Você é um especialista em LGPD, segurança da informação e arquitetura de dados.

Sua tarefa é comparar um SCHEMA DE BANCO DE DADOS e um TERMO DE COMPROMISSO com a Lei Geral de Proteção de Dados (LGPD).

===== LEI =====
{lgpd_context}

===== SCHEMA =====
{schema_sql}

===== TERMO DE COMPROMISSO =====
{terms_text}

===== INSTRUÇÃO OBRIGATÓRIA =====
Responda APENAS em JSON válido, sem markdown, sem comentários e sem texto extra.

Estrutura exata do JSON:
{{
  "overall_status": "COMPLIANT | PARTIAL | NON_COMPLIANT",
  "summary": "string",
  "points_correct": ["string"],
  "points_outside_law": ["string"],
  "applicable_articles": [{{
    "article": "string",
    "description": "string"
  }}],
  "risks": ["string"],
  "recommendations": ["string"]
}}

Critérios:
- Identifique dados pessoais e finalidades do processamento.
- Compare com os artigos da LGPD e os princípios da lei.
- Destaque pontos que atendem ao requisito e pontos que violam ou deixam brechas.
- Liste artigos relevantes da LGPD, com explicações curtas.
- Indique riscos corretos e ações prioritárias.
- Se não houver informações suficientes, sinalize isso de forma objetiva.
- Todos os valores textuais do JSON (summary, points_correct, points_outside_law, description, risks, recommendations) devem estar em português do Brasil (pt-BR), independentemente do idioma do schema ou do termo analisado.

A resposta deve ser um objeto JSON válido, sem trechos em markdown.

LEMBRETE FINAL: escreva todos os valores de texto do JSON em português do Brasil (pt-BR), nunca em inglês."""

    GENERATE_GOLDEN_DATASET = """IDIOMA OBRIGATÓRIO: PORTUGUÊS DO BRASIL (pt-BR). Não responda em inglês ou em qualquer outro idioma.

Você é um especialista em LGPD e em avaliação de sistemas de RAG (Retrieval-Augmented Generation).

Sua tarefa é gerar um GOLDEN DATASET de perguntas e respostas de referência para avaliar, via RAGAS, um chatbot que responde perguntas EXCLUSIVAMENTE com base no relatório de conformidade LGPD abaixo.

===== RELATÓRIO DE CONFORMIDADE LGPD =====
{report_context}

===== INSTRUÇÕES =====
Gere exatamente {num_questions} perguntas, variadas entre si (não repita o mesmo achado com palavras diferentes), cobrindo diferentes seções do relatório (pontos corretos, pontos fora da lei, artigos aplicáveis, riscos, recomendações). Cada pergunta deve ser algo que um usuário real do produto (gestor de compliance, DPO, desenvolvedor) perguntaria ao consultar esse relatório.

Cada "reference_answer" deve:
- Ser a resposta correta e completa à pergunta, baseada EXCLUSIVAMENTE no conteúdo do relatório acima (não invente achados que não estejam no relatório).
- Ser objetiva, mas completa o suficiente para servir de gabarito (ground truth) em uma avaliação automática de qualidade de resposta.

===== INSTRUÇÃO OBRIGATÓRIA DE FORMATO =====
Responda APENAS com um array JSON válido, sem markdown, sem comentários e sem texto fora do array.

Estrutura exata do JSON:
[
  {{
    "question": "string",
    "reference_answer": "string"
  }}
]

LEMBRETE FINAL: escreva as perguntas e respostas em português do Brasil (pt-BR), nunca em inglês. Não inclua nenhum texto antes ou depois do array JSON."""

    ANSWER_REPORT_QUESTION = """IDIOMA OBRIGATÓRIO: PORTUGUÊS DO BRASIL (pt-BR). Não responda em inglês ou em qualquer outro idioma.

Você é um assistente especializado em compliance com a LGPD e em engenharia de dados/segurança aplicada.

Sua tarefa é responder à pergunta do usuário sobre a base de conhecimento abaixo. Os FATOS sobre o que foi encontrado (pontos corretos, pontos fora da lei, riscos, artigos aplicáveis) vêm EXCLUSIVAMENTE dos trechos do relatório — não invente achados que não estejam neles, e diga claramente quando o relatório não tiver a informação necessária.

Quando a pergunta for sobre COMO CORRIGIR ou ADEQUAR um ponto levantado no relatório (ex.: "como corrigir isso", "que tecnologia usar", "boas práticas para resolver"), você PODE e DEVE ir além do texto literal do relatório: proponha soluções técnicas concretas — tecnologias, bibliotecas, padrões de arquitetura e boas práticas de mercado — para sanar o problema apontado, sempre conectando a recomendação ao artigo/ponto específico do relatório que a motivou. Nesse caso, deixe claro que a recomendação é uma sugestão de adequação sua, e não parte literal do relatório.

===== TRECHOS DO RELATÓRIO DE CONFORMIDADE =====
{report_context}

===== PERGUNTA =====
{question}

===== RESPOSTA REQUERIDA =====
Responda de forma direta e objetiva. Primeiro situe o achado do relatório (citando trecho/artigo relevante); depois, se a pergunta pedir correção, liste as recomendações técnicas práticas (tecnologias/bibliotecas/padrões específicos, não genéricos) para resolver o problema. Não repita o relatório inteiro, apenas o necessário para responder.

LEMBRETE FINAL: responda em português do Brasil (pt-BR), nunca em inglês."""


def build_schema_analysis_prompt(
    lgpd_context: str,
    document_content: str,
) -> str:
    """
    Constrói prompt para análise de schema com contexto LGPD.

    Args:
        lgpd_context: Texto completo da LGPD
        document_content: Conteúdo do schema/documento a analisar

    Returns:
        Prompt formatado com contextos
    """
    return PromptTemplates.ANALYZE_SCHEMA_COMPLIANCE.format(
        lgpd_context=lgpd_context,
        document_content=document_content,
    )


def build_terms_analysis_prompt(
    lgpd_context: str,
    document_content: str,
) -> str:
    """
    Constrói prompt para análise de termo de compromisso com contexto LGPD.

    Args:
        lgpd_context: Texto completo da LGPD
        document_content: Conteúdo do termo de compromisso a analisar

    Returns:
        Prompt formatado com contextos
    """
    return PromptTemplates.ANALYZE_TERMS_COMPLIANCE.format(
        lgpd_context=lgpd_context,
        document_content=document_content,
    )


def build_compliance_report_prompt(
    lgpd_context: str,
    document_content: str,
    previous_analysis: str,
) -> str:
    """
    Constrói prompt para geração de relatório de compliance.

    Args:
        lgpd_context: Texto completo da LGPD
        document_content: Conteúdo original do documento
        previous_analysis: Análise anterior do documento

    Returns:
        Prompt formatado com contextos
    """
    return PromptTemplates.GENERATE_COMPLIANCE_REPORT.format(
        lgpd_context=lgpd_context,
        document_content=document_content,
        previous_analysis=previous_analysis,
    )


def build_structured_schema_terms_prompt(
    lgpd_context: str,
    schema_sql: str,
    terms_text: str,
) -> str:
    """Constrói prompt para análise estruturada de schema + termo contra a LGPD."""
    return PromptTemplates.ANALYZE_SCHEMA_TERMS_STRUCTURED.format(
        lgpd_context=lgpd_context,
        schema_sql=schema_sql,
        terms_text=terms_text,
    )


def build_report_answer_prompt(report_context: str, question: str) -> str:
    """Constrói prompt para responder uma pergunta com base em trechos do relatório de compliance."""
    return PromptTemplates.ANSWER_REPORT_QUESTION.format(
        report_context=report_context,
        question=question,
    )


def build_golden_dataset_prompt(report_context: str, num_questions: int) -> str:
    """Constrói prompt para gerar um golden dataset (pergunta + resposta de referência) a partir
    do relatório de compliance publicado, para uso na avaliação RAGAS."""
    return PromptTemplates.GENERATE_GOLDEN_DATASET.format(
        report_context=report_context,
        num_questions=num_questions,
    )
