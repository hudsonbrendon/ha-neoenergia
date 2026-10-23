# Engenharia reversa — Agência Virtual Neoenergia (Cosern)

O app Android da Cosern (`br.com.neoenergia.app`, "Neoenergia SA") foi removido
dos mirrors de APK, então a RE foi feita sobre o **web app da Agência Virtual**
`https://agenciavirtual.neoenergia.com` (Angular SPA), que usa o mesmo backend.

## Arquitetura

- SPA Angular; bundle `main.*.js` com os corpos de classe preservados (webpack
  não totalmente minificado) — deu para ler services, DTOs e o objeto
  `environment`.
- Gateway de API: **WSO2 API Manager** em `https://apineprd.neoenergia.com`
  (região **NE**, cobre Cosern/Coelba/Celpe). SE usa `apiseprd.neoenergia.com`.
  Há proteção Akamai (cookies `_abck`/`bm_sz`) mas não bloqueou as chamadas de API.
- `environment` do portal publicado: `canal: AGU`, `host = https://apineprd.neoenergia.com`,
  `hostanl = https://avapineanl.neoenergia.com`.

## Autenticação — OAuth2 password grant

`LoginDTO` → `POST {host}/token` (form-urlencoded):

```
grant_type=password
client_id=<por canal>
client_secret=<por canal>
username=<CPF/CNPJ>
password=<senha>
scope=openid
```

Resposta: `access_token`, `refresh_token`, `id_token`, `expires_in`. Chamadas de
dados usam `Authorization: Bearer <access_token>`. Refresh via
`grant_type=refresh_token`.

### ⚠️ Credencial do gateway (bloqueio conhecido)

`identificaClientIdPorCanal()`/`identificaClientSecretPorCanal()` retornam, por
canal (todos terminam em `a`, sinal de ofuscação):

| canal | client_id | client_secret |
|---|---|---|
| AGR | `CwYFvFj_DDtLJedIu9y1n1hcOd8a` | `f9ZJfZEhCpj8db5nYrhl_tWxhaMa` |
| AGC (Coelba) | `YicYeqO8E_XACfWfjeQgLSo6Md0a` | `FFiuHe1wEiSKJZRU8ENqMC4sA0oa` |
| AGP (Celpe) | `uScXQQwAe2qxKATIvv1EfB77IoYa` | `agbpXX7kWfSfuOCH8cdfzwf7Riga` |
| AGE (Elektro) | `7fUw6KahtPMfaNz_8DQ241Fqo2Ia` | `KRQZu1qipiNr3N2v61qOuskJYmAa` |
| default (AGU) | `a_vrfGrkqevUPzXWSZbC_KwkEX8a` | `ZmILVM_atdaM7C7O6sayq029XM4a` |

**Porém o gateway de produção responde `invalid_client` para todos** (testado via
form e via Basic auth no `/token`). Ou seja, esses valores são transformados/
decifrados em runtime antes do request. A credencial real precisa ser **capturada
de um login verdadeiro** — veja `scripts/capturar_credencial.py`. Depois,
informe `client_id`/`client_secret` nos campos avançados da integração.

## Endpoints (de `environment.endpoints`, caso NE celpe/coelba/cosern)

Base `${host}` = `https://apineprd.neoenergia.com`.

| Chave | URL | Uso |
|---|---|---|
| token | `/token` | OAuth2 |
| selecaoImovel | `/imoveis/1.1.0/` | `clientes/{documento}/ucs` → UCs (`consultarImoveis`) |
| multiloginServicos | `/multilogin/2.0.0/` | base dos serviços logados |
| faturas | `…/servicos/faturas/ucs/faturas` (GET, params documentoCliente, uc) | faturas da UC |
| faturas simplificada | `…/servicos/faturas/faturas-simplificada` | débitos / 2ª via |
| minha-conta | `…/servicos/minha-conta` (GET) | dados da conta (`consultarMinhaConta`) |
| histórico | `/multilogin/2.0.0/servicos/historicos/` | histórico de consumo |
| consultar-debitos | `…/servicos/consultar-debitos` | débitos |
| bandeira | `/bandeira-tarifaria/1.0.0/` | bandeira tarifária |
| autoleitura | `…/servicos/autoleitura/ucs/{uc}` | autoleitura |
| boleto-unico, pix, pagamentos, protocolo, religação, débito-automático, ligação-nova, troca-titularidade, tarifa-social, ouvidoria … | vários | referência |

Shapes de resposta (campos de fatura/UC/consumo) são inferidos e marcados para
ajuste — confirmar com a captura real (`scripts/capturar_credencial.py` também
coleta as URLs/respostas pós-login).

## Achado após login real (23/10/2026)

- O login de verdade **não** é o OAuth password grant do `LoginDTO`. O site faz
  `POST {hostanl}/areanaologada/2.0.0/autentica` com JSON
  `{usuario, senha, canalSolicitante: "AGU", recaptcha}`, e quem responde é um
  BFF que faz o OAuth do lado do servidor com o próprio client (o `azp` do JWT é
  `XglvQJfHEWsQCK8li2urGlwf_EEa`, que não aparece no bundle). A resposta é
  `{token: {ne, se}}`, um access token JWT RS256 por região.
- **O servidor exige reCAPTCHA v3** (`O parâmetro 'recaptcha' é obrigatório` /
  `Invalid Captcha`). O token vale 1 h e **não tem refresh_token**.
- Por isso não dá pra ter uma integração headless contínua sem contornar o
  captcha, e isso não foi feito de propósito.
- Formato confirmado de `clientes/{doc}/ucs`: `{ucs:[{status, uc, codigoUcAneel,
  nomeCliente, instalacao, local{endereco,bairro,municipio,cep,uf},
  enderecoEntrega{…}, grupoTensao, contrato, dt_inicio, dt_fim, …}],
  e_resultado, retorno{id,tipo,numero,mensagem}}`.
- Bandeira: `{tipo, cor, mensagem, mesReferencia}`.

## Status

Mapa de endpoints e formatos: documentados. **Integração headless: bloqueada
pelo reCAPTCHA v3 no login.** Os caminhos legítimos estão no README.
