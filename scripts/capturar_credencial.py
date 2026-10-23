"""Captura a credencial REAL do gateway (client_id/secret) + shapes de resposta.

Os client_id/secret do bundle Angular retornam `invalid_client` no gateway de
produção (são decifrados em runtime). Este script usa o browser-harness para
observar o tráfego de rede enquanto VOCÊ loga na Agência Virtual
(https://agenciavirtual.neoenergia.com) e extrai, do POST para `/token`:

- o `client_id`/`client_secret` reais (do corpo do form ou do header Basic);
- as URLs e os formatos das respostas de UCs/faturas/consumo.

A sua SENHA é redigida (nunca é impressa/salva). Rode com o browser-harness
disponível e a aba de login aberta; faça o login quando mandado.

    python3 scripts/capturar_credencial.py   # (dispara via browser-harness)

Na prática é mais simples rodar o bloco abaixo direto pelo browser-harness.
"""

from __future__ import annotations

SNIPPET = r'''
import base64, json, time, urllib.parse
new_tab("https://agenciavirtual.neoenergia.com/#/login"); cdp("Page.bringToFront")
cdp("Network.enable"); drain_events()
print(">>> FACA O LOGIN AGORA (Cosern + CPF/CNPJ + senha). Aguardando /token ...")
cred=None; deadline=time.time()+240
reqbody={}
while time.time()<deadline and not cred:
    for e in (drain_events() or []):
        if not isinstance(e,dict): continue
        p=e.get("params",{}); req=p.get("request",{})
        url=req.get("url","")
        if url.endswith("/token") and e.get("method")=="Network.requestWillBeSent":
            hdr={k.lower():v for k,v in (req.get("headers") or {}).items()}
            post=req.get("postData","")
            form=dict(urllib.parse.parse_qsl(post))
            cid=form.get("client_id"); sec=form.get("client_secret")
            auth=hdr.get("authorization","")
            if auth.lower().startswith("basic "):
                try:
                    dec=base64.b64decode(auth.split(" ",1)[1]).decode()
                    if ":" in dec: cid,sec=dec.split(":",1)
                except Exception: pass
            cred={"client_id":cid,"client_secret":sec}  # senha NAO incluida
    time.sleep(2)
print("CREDENCIAL:", json.dumps(cred))
# coleta algumas URLs de dados pos-login
apis=set()
for e in (drain_events() or []):
    u=((e.get("params") or {}).get("request") or {}).get("url","")
    if "apineprd" in u or "apiseprd" in u: apis.add(u.split("?")[0])
print("APIS:", json.dumps(sorted(apis)[:40]))
'''

if __name__ == "__main__":
    print("Cole o SNIPPET abaixo num heredoc do browser-harness:\n")
    print(SNIPPET)
