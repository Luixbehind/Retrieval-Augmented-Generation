"""Gera termo_compromisso.pdf a partir do texto abaixo (reportlab). Script de uso único, pode ser apagado depois de gerar o PDF."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_JUSTIFY

styles = getSampleStyleSheet()
title_style = ParagraphStyle("TitleCustom", parent=styles["Title"], fontSize=14, spaceAfter=14)
h2_style = ParagraphStyle("H2Custom", parent=styles["Heading2"], fontSize=11, spaceBefore=12, spaceAfter=6)
body_style = ParagraphStyle("BodyCustom", parent=styles["BodyText"], fontSize=10, leading=14, alignment=TA_JUSTIFY, spaceAfter=8)

doc = SimpleDocTemplate(
    "data/production_scenario/termo_compromisso.pdf",
    pagesize=A4,
    topMargin=2 * cm,
    bottomMargin=2 * cm,
    leftMargin=2 * cm,
    rightMargin=2 * cm,
    title="Termo de Compromisso de Tratamento de Dados Pessoais - SaudeConecta",
)

story = []
story.append(Paragraph("Termo de Compromisso de Tratamento de Dados Pessoais", title_style))
story.append(Paragraph(
    "SaudeConecta Tecnologia em Saude Ltda. (“Controladora”), operadora da plataforma de "
    "telemedicina “SaudeConecta”, assume perante seus usuários (pacientes, médicos e demais "
    "profissionais cadastrados) o compromisso de tratar dados pessoais em conformidade com a Lei nº "
    "13.709/2018 (Lei Geral de Proteção de Dados Pessoais - LGPD) e com as normas setoriais do "
    "Conselho Federal de Medicina aplicáveis à telemedicina.",
    body_style,
))

story.append(Paragraph("1. Dados pessoais coletados", h2_style))
story.append(Paragraph(
    "Coletamos dados cadastrais (nome completo, CPF, e-mail, telefone, data de nascimento) para "
    "identificação do titular e emissão de documentos fiscais. De médicos, coletamos adicionalmente "
    "número de registro no CRM e especialidade. Para viabilização das consultas, coletamos dados de "
    "saúde fornecidos pelo próprio paciente (sintomas, histórico de condições crônicas, medicações em "
    "uso, alérgias) e registros gerados durante o atendimento (notas de diagnóstico, prescrições, "
    "gravação e transcrição do áudio da consulta).",
    body_style,
))

story.append(Paragraph("2. Base legal e consentimento", h2_style))
story.append(Paragraph(
    "O tratamento de dados cadastrais tem como base legal a execução de contrato (Art. 7º, V, LGPD). "
    "O tratamento de dados de saúde, por se tratar de dado pessoal sensível (Art. 5º, II), é realizado "
    "mediante consentimento específico e destacado do titular (Art. 11, I), coletado no momento do "
    "cadastro e registrado com data, hora e versão dos termos aceitos. O titular pode revogar o "
    "consentimento a qualquer momento, sem prejuízo dos atendimentos já realizados.",
    body_style,
))

story.append(Paragraph("3. Finalidade do tratamento", h2_style))
story.append(Paragraph(
    "Os dados são utilizados exclusivamente para: (i) viabilizar o agendamento e a realização de "
    "consultas por telemedicina; (ii) gerar e armazenar o prontuário eletrônico do paciente; (iii) "
    "processar pagamentos das consultas; (iv) cumprir obrigações legais e regulatórias aplicáveis a "
    "serviços de saúde; e (v) mediante consentimento à parte, envio de comunicações de marketing "
    "sobre novos serviços.",
    body_style,
))

story.append(Paragraph("4. Compartilhamento com terceiros", h2_style))
story.append(Paragraph(
    "Dados de pagamento são compartilhados com processadoras de pagamento estritamente para "
    "viabilizar a transação. Gravações e transcrições de consulta podem ser processadas por "
    "fornecedor de infraestrutura de áudio/nuvem sob contrato de confidencialidade e instruções "
    "documentadas de tratamento. A Controladora não compartilha, vende ou cede dados de saúde ou "
    "dados cadastrais para parceiros de publicidade ou finalidades de ad targeting.",
    body_style,
))

story.append(Paragraph("5. Retenção e eliminação", h2_style))
story.append(Paragraph(
    "Prontuários eletrônicos são retidos pelo prazo mínimo de 20 (vinte) anos a contar do último "
    "atendimento, conforme Resolução CFM aplicável. Gravações de áudio/vídeo e transcrições são "
    "retidas pelo mesmo prazo do prontuário e eliminadas de forma segura ao final do período de "
    "retenção, mediante rotina periódica de expurgo. Dados cadastrais são mantidos enquanto durar o "
    "vínculo do titular com a plataforma e por até 5 (cinco) anos após o encerramento da conta, para "
    "cumprimento de obrigações fiscais.",
    body_style,
))

story.append(Paragraph("6. Direitos do titular", h2_style))
story.append(Paragraph(
    "O titular pode solicitar, a qualquer momento e mediante requisição ao canal "
    "privacidade@saudeconecta.com.br, a confirmação da existência de tratamento, o acesso, a "
    "correção, a portabilidade, a anonimização ou a eliminação de seus dados pessoais, bem como "
    "revogar consentimentos previamente concedidos, nos termos do Art. 18 da LGPD. As solicitações "
    "são respondidas em até 15 (quinze) dias úteis.",
    body_style,
))

story.append(Paragraph("7. Segurança da informação", h2_style))
story.append(Paragraph(
    "A Controladora adota medidas técnicas e administrativas aptas a proteger os dados pessoais de "
    "acessos não autorizados e de situações acidentais ou ilícitas de destruição, perda, alteração, "
    "comunicação ou difusão, incluindo controle de acesso baseado em papel (role-based access "
    "control), criptografia de dados em trânsito e trilha de auditoria de acessos a dados sensíveis. "
    "Dados sensíveis de saúde e documentos de identificação (CPF) são armazenados com criptografia "
    "em nível de coluna no banco de dados de produção.",
    body_style,
))

story.append(Paragraph("8. Encarregado de Dados (DPO)", h2_style))
story.append(Paragraph(
    "A Controladora designa encarregado pelo tratamento de dados pessoais (Data Protection Officer), "
    "responsável por receber comunicações de titulares e da Autoridade Nacional de Proteção de Dados "
    "(ANPD), bem como por orientar os funcionários quanto às práticas de proteção de dados pessoais, "
    "podendo ser contatado pelo canal dpo@saudeconecta.com.br.",
    body_style,
))

doc.build(story)
print("PDF gerado em data/production_scenario/termo_compromisso.pdf")
