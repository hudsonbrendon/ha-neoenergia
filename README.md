# Neoenergia (Cosern / Coelba / Celpe) — Home Assistant

Integração não-oficial que traz os dados da sua conta de energia **Neoenergia**
— incluindo a **Cosern** (Rio Grande do Norte) — para o Home Assistant: faturas,
consumo (kWh) e bandeira tarifária, por unidade consumidora (UC).

Feita por engenharia reversa da **Agência Virtual** web
(`agenciavirtual.neoenergia.com`). Detalhes em
[`REVERSE_ENGINEERING.md`](REVERSE_ENGINEERING.md).

> Projeto pessoal, sem vínculo com a Neoenergia. Use com a sua própria conta.

## ⚠️ Antes de usar: credencial do gateway

O login é OAuth2 (CPF/CNPJ + senha da Agência Virtual), mas o gateway WSO2 exige
um `client_id`/`client_secret` de cliente OAuth. Os valores achados no código do
site estão **ofuscados** e o servidor os recusa (`invalid_client`). Você precisa
**capturar os reais** uma vez:

1. Com o `browser-harness` instalado, rode o conteúdo de
   `scripts/capturar_credencial.py` e faça login na Agência Virtual quando pedido.
   Ele imprime `client_id`/`client_secret` reais (sua senha é redigida).
2. Informe esses dois valores nos campos avançados ao adicionar a integração.

Sem isso, o login falha com "invalid_auth / invalid_client".

## Instalação (HACS)

1. HACS → repositórios customizados → `hudsonbrendon/ha-neoenergia` (Integration).
2. Instale e reinicie o Home Assistant.
3. Adicionar Integração → **Neoenergia** → informe CPF/CNPJ, senha, distribuidora
   (**cosern** para RN) e, se já capturou, `client_id`/`client_secret`.

## Entidades (um dispositivo por UC)

- **Fatura atual** — valor; vencimento, status, referência, código de barras e
  PIX nos atributos.
- **Consumo** (kWh) — consumo mais recente + histórico nos atributos.
- **Bandeira tarifária** — cor/nome vigente (global).

Atualização a cada 6 h (cloud polling).

## Status

- ✅ Auth OAuth2 e mapa de endpoints: completos (RE do SPA).
- ⏳ Credencial real do gateway + shapes exatos de resposta: dependem de 1
  captura de login (`scripts/capturar_credencial.py`). Os sensores leem os
  campos de forma tolerante e serão afinados após a captura.

## Desenvolvimento

```bash
python3 -I tests/test_api.py
```

## Aviso

A API é privada e pode mudar sem aviso. A integração só faz leituras.
