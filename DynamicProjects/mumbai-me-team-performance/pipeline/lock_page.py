"""The ME dashboard with a sign-in, as ONE static page for HTML Drop (5 Nov 2026; the same method as the ECS Collection Tracker
on HTML Drop). Every page - Kushal Sharma's whole dashboard and each manager's own page - is gzipped and encrypted inside one
HTML file; a login's password unlocks only that login's page, in the viewer's browser. No server is needed: upload the file at
the usual link (mumbai-me-team-performance).

Writes  the sign-in page: in the shared kit the kit's own "Mumbai ME Team Performance.html" (the page HTML Drop shows);
        on the analysis PC upload\\Mumbai ME Team Performance.html
Reads   the unlocked pages (Mumbai ME Team Performance.html and manager_pages\\<code>.html, made by build_review.py) and
        vault_keys.json (per login: name, page, salt and the key made from the password) - in the shared kit all three sit
        in the private folder (pipeline\\kitpaths.py), never in the folder HTML Drop shows

    python pipeline\\lock_page.py                                   rebuild the upload page (build_review.py runs this)
    python pipeline\\lock_page.py --set-password <login> <password> set / change a password, then rebuild
    python pipeline\\lock_page.py --list                            the logins and their pages

Method (as the ECS tracker): each page gets a new random 256-bit key at every build; page = ChaCha20(page key, nonce,
gzip(html)). Each login: k = PBKDF2-HMAC-SHA256(password, salt, 100,000 rounds); the login's page key is stored as
ChaCha20(k, nonce, page key) with a 16-byte HMAC-SHA256(k, nonce + wrapped key) check. The browser does the same in plain
JavaScript (works on http, where the browser's own crypto is not available). A wrong password opens nothing.
Note: the whole file can be downloaded, so a password can be guessed offline without any lock; its strength is the only
protection.
"""
import base64
import gzip
import hashlib
import hmac
import json
import os
import secrets
import sys

PIPE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(PIPE)
sys.path.insert(0, PIPE)
import kitpaths   # shared kit: unlocked pages and vault_keys.json in the private folder, the sign-in page = the kit's page
FULL, MGR, KEYS, OUT = kitpaths.FULL, kitpaths.MGR, kitpaths.KEYS, kitpaths.SIGNIN
OUT_DIR = os.path.dirname(OUT)
ITER = 100_000
b64 = lambda b: base64.b64encode(b).decode()


def chacha20(key, nonce, data):
    """ChaCha20 (RFC 8439), block counter from 0, 96-bit nonce - the same as the page's JavaScript"""
    try:
        import numpy as np
    except ImportError:
        return _chacha20_py(key, nonce, data)
    n = (len(data) + 63) // 64
    st = np.zeros((n, 16), dtype=np.uint32)
    st[:, 0:4] = (0x61707865, 0x3320646E, 0x79622D32, 0x6B206574)
    st[:, 4:12] = np.frombuffer(key, dtype="<u4")
    st[:, 12] = np.arange(n, dtype=np.uint32)
    st[:, 13:16] = np.frombuffer(nonce, dtype="<u4")
    x = st.copy()

    def qr(a, b, c, d):
        for p, q, r, s in ((a, b, d, 16), (c, d, b, 12), (a, b, d, 8), (c, d, b, 7)):
            x[:, p] += x[:, q]
            v = x[:, r] ^ x[:, p]
            x[:, r] = (v << np.uint32(s)) | (v >> np.uint32(32 - s))
    for _ in range(10):
        qr(0, 4, 8, 12); qr(1, 5, 9, 13); qr(2, 6, 10, 14); qr(3, 7, 11, 15)
        qr(0, 5, 10, 15); qr(1, 6, 11, 12); qr(2, 7, 8, 13); qr(3, 4, 9, 14)
    ks = (x + st).astype("<u4").tobytes()[:len(data)]
    return (np.frombuffer(data, dtype=np.uint8) ^ np.frombuffer(ks, dtype=np.uint8)).tobytes()


def _chacha20_py(key, nonce, data):
    import struct
    M = 0xFFFFFFFF
    R = lambda v, c: ((v << c) & M) | (v >> (32 - c))
    k = list(struct.unpack("<8I", key)); nn = list(struct.unpack("<3I", nonce)); out = bytearray(len(data))
    for blk in range((len(data) + 63) // 64):
        s = [0x61707865, 0x3320646E, 0x79622D32, 0x6B206574] + k + [blk & M] + nn; x = s[:]
        for _ in range(10):
            for a, b, c, d in ((0, 4, 8, 12), (1, 5, 9, 13), (2, 6, 10, 14), (3, 7, 11, 15), (0, 5, 10, 15), (1, 6, 11, 12), (2, 7, 8, 13), (3, 4, 9, 14)):
                x[a] = (x[a] + x[b]) & M; x[d] = R(x[d] ^ x[a], 16); x[c] = (x[c] + x[d]) & M; x[b] = R(x[b] ^ x[c], 12)
                x[a] = (x[a] + x[b]) & M; x[d] = R(x[d] ^ x[a], 8); x[c] = (x[c] + x[d]) & M; x[b] = R(x[b] ^ x[c], 7)
        ks = struct.pack("<16I", *[(x[i] + s[i]) & M for i in range(16)])
        o = blk * 64
        for i, byte in enumerate(data[o:o + 64]):
            out[o + i] = byte ^ ks[i]
    return bytes(out)


def _selftest():
    """RFC 8439 2.4.2 (counter 1 = our counter 0 after one skipped block)"""
    key = bytes(range(32)); nonce = bytes.fromhex("000000000000004a00000000")
    pt = b"Ladies and Gentlemen of the class of '99: If I could offer you only one tip for the future, sunscreen would be it."
    ct = chacha20(key, nonce, bytes(64) + pt)[64:]
    assert ct[:16].hex() == "6e2e359a2568f98041ba0728dd0d6981", "ChaCha20 self-test failed"


def load_keys():
    with open(KEYS, encoding="utf-8") as f:
        return json.load(f)


def save_keys(k):
    tmp = KEYS + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(k, f, ensure_ascii=False, indent=1)
    os.replace(tmp, KEYS)


def page_file(page):
    return FULL if page == "full" else os.path.join(MGR, f"{page}.html") if page and page.isalnum() else None


BAR = ('<div class="jd-signbar" style="position:fixed;right:12px;bottom:12px;z-index:2147483000;background:#fff;color:#14213D;'
       'border:1px solid #D9DEE7;border-radius:999px;padding:5px 12px;font:12px/1.4 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;'
       'box-shadow:0 1px 4px rgba(20,33,61,.12)">Signed in: <b>%NAME%</b> · <a href="#" style="color:#1F5FAD" '
       'onclick="try{sessionStorage.removeItem(\'jdme_s\')}catch(e){};location.replace(location.pathname);return false;">Sign out</a></div>'
       '<style>@media print{.jd-signbar{display:none}}</style>')


def build(log=print):
    _selftest()
    if not os.path.exists(KEYS):
        log("lock_page: no vault_keys.json - the sign-in page was not built.")
        return None
    keys = load_keys()
    it = int(keys.get("iter", ITER)); logins = keys["logins"]
    F, U, pkey = {}, {}, {}
    for login, e in logins.items():
        page = e["page"]
        if page in pkey:
            continue
        p = page_file(page)
        if not p or not os.path.exists(p):
            log(f"lock_page: the page of {login} ({page}) is not there - that login will not open.")
            continue
        raw = open(p, "rb").read()
        bar = BAR.replace("%NAME%", e.get("name", login).replace("<", "&lt;")).encode("utf-8")
        i = raw.rfind(b"</body>")
        raw = raw[:i] + bar + raw[i:] if i >= 0 else raw + bar
        kf, nf = secrets.token_bytes(32), secrets.token_bytes(12)
        F[page] = {"n": b64(nf), "c": b64(chacha20(kf, nf, gzip.compress(raw, 9)))}
        pkey[page] = kf
    for login, e in logins.items():
        if e["page"] not in pkey:
            continue
        ku = bytes.fromhex(e["key"])
        nw = secrets.token_bytes(12); w = chacha20(ku, nw, pkey[e["page"]])
        U[login] = {"s": e["salt"], "k": [[e["page"], b64(nw), b64(w)]], "t": b64(hmac.new(ku, nw + w, hashlib.sha256).digest()[:16])}
    vault = json.dumps({"iter": it, "U": U, "F": F}, separators=(",", ":"))
    os.makedirs(OUT_DIR, exist_ok=True)
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(GATE.replace("/*VAULT*/", vault.replace("</", "<\\/")))
    os.replace(tmp, OUT)
    log(f"Wrote {OUT} ({os.path.getsize(OUT) / 1e6:.1f} MB, {len(U)} logins, {len(F)} pages) - upload this file to HTML Drop.")
    return OUT


def set_password(login, pw, name=None, page=None):
    keys = load_keys() if os.path.exists(KEYS) else {"iter": ITER, "logins": {}}
    e = keys["logins"].get(login, {})
    if name: e["name"] = name
    if page: e["page"] = page
    if "page" not in e:
        sys.exit(f"New login {login!r}: give --page full|<manager code> and --name \"Full Name\".")
    salt = secrets.token_bytes(16)
    e.update({"salt": b64(salt), "key": hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), salt, int(keys.get("iter", ITER))).hex()})
    keys["logins"][login] = e
    save_keys(keys)
    print(f"Password set for {login}.")


GATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sign in · ME team, Mumbai</title><script>try{if(sessionStorage.getItem('jdme_s'))document.documentElement.className='rs'}catch(e){}</script><style>
:root{--navy:#0B1B3F;--ink:#14213D;--mu:#5B6475;--line:#D9DEE7;--bg:#F4F6FA;--red:#B8322A}
*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.card{width:min(360px,calc(100vw - 32px));background:#fff;border:1px solid var(--line);border-top:4px solid var(--navy);border-radius:10px;padding:26px 26px 22px}
h1{font-size:19px;margin:0 0 4px}p.s{margin:0 0 18px;color:var(--mu);font-size:13px}label{display:block;font-size:13px;font-weight:600;margin:12px 0 5px}
input{width:100%;padding:9px 10px;border:1px solid var(--line);border-radius:6px;font:inherit}input:focus{outline:2px solid #2a78d6;outline-offset:1px;border-color:#2a78d6}
button{margin-top:18px;width:100%;padding:10px;border:0;border-radius:6px;background:var(--navy);color:#fff;font:inherit;font-weight:600;cursor:pointer}button:disabled{opacity:.7;cursor:default}
.rs .card{visibility:hidden}.err{margin:12px 0 0;color:var(--red);font-size:13px;min-height:1px}.ft{margin:16px 0 0;color:var(--mu);font-size:12px}[hidden]{display:none!important}
</style></head><body>
<form class="card" id="gForm" hidden autocomplete="on"><h1>ME team, Mumbai</h1>
<label for="gU">Login ID</label><input id="gU" name="username" autocomplete="username" required>
<label for="gP">Password</label><input id="gP" name="password" type="password" autocomplete="current-password" required>
<p class="err" id="gE" role="alert"></p><button id="gB" type="submit">Sign in</button></form>
<div class="card" id="gLoad"><h1>ME team, Mumbai</h1><p class="s" style="margin:0">Opening the dashboard…</p></div>
<script id="vault" type="application/json">/*VAULT*/</script>
<script>
(function(){
const V=JSON.parse(document.getElementById('vault').textContent);
const b64=s=>{const b=atob(s),u=new Uint8Array(b.length);for(let i=0;i<b.length;i++)u[i]=b.charCodeAt(i);return u;};
const toB64=u=>{let s='';for(let i=0;i<u.length;i++)s+=String.fromCharCode(u[i]);return btoa(s);};
const KK=new Uint32Array([0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,
0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,
0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,
0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2]);
const IV=[0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19],W=new Uint32Array(64);
function cmp(H,p,o){for(let i=0;i<16;i++)W[i]=(p[o+4*i]<<24)|(p[o+4*i+1]<<16)|(p[o+4*i+2]<<8)|p[o+4*i+3];
 for(let i=16;i<64;i++){const a=W[i-15],b=W[i-2];W[i]=(W[i-16]+(((a>>>7)|(a<<25))^((a>>>18)|(a<<14))^(a>>>3))+W[i-7]+(((b>>>17)|(b<<15))^((b>>>19)|(b<<13))^(b>>>10)))|0;}
 let a=H[0],b=H[1],c=H[2],d=H[3],e=H[4],f=H[5],g=H[6],h=H[7];
 for(let i=0;i<64;i++){const t1=(h+(((e>>>6)|(e<<26))^((e>>>11)|(e<<21))^((e>>>25)|(e<<7)))+((e&f)^(~e&g))+KK[i]+W[i])|0;
  const t2=((((a>>>2)|(a<<30))^((a>>>13)|(a<<19))^((a>>>22)|(a<<10)))+((a&b)^(a&c)^(b&c)))|0;h=g;g=f;f=e;e=(d+t1)|0;d=c;c=b;b=a;a=(t1+t2)|0;}
 H[0]+=a;H[1]+=b;H[2]+=c;H[3]+=d;H[4]+=e;H[5]+=f;H[6]+=g;H[7]+=h;}
function out(H){const o=new Uint8Array(32);for(let i=0;i<8;i++){o[4*i]=H[i]>>>24;o[4*i+1]=H[i]>>>16;o[4*i+2]=H[i]>>>8;o[4*i+3]=H[i];}return o;}
function sha(m,H0,pre){const H=new Uint32Array(H0||IV),l=m.length,n=((l+9+63)>>6)<<6,p=new Uint8Array(n);p.set(m);p[l]=0x80;const bits=(l+(pre||0))*8;
 p[n-4]=bits>>>24;p[n-3]=bits>>>16;p[n-2]=bits>>>8;p[n-1]=bits;p[n-5]=Math.floor(bits/4294967296);for(let o=0;o<n;o+=64)cmp(H,p,o);return out(H);}
function pads(key){if(key.length>64)key=sha(key);const k=new Uint8Array(64);k.set(key);const i=k.map(x=>x^0x36),o=k.map(x=>x^0x5c);
 const Hi=new Uint32Array(IV),Ho=new Uint32Array(IV);cmp(Hi,i,0);cmp(Ho,o,0);return [Hi,Ho];}
function hmac(key,m){const [Hi,Ho]=pads(key);return sha(sha(m,Hi,64),Ho,64);}
function pbkdf2(pw,salt,it){const [Hi,Ho]=pads(pw);const s=new Uint8Array(salt.length+4);s.set(salt);s[s.length-1]=1;
 let U=sha(sha(s,Hi,64),Ho,64);const T=U.slice(),blk=new Uint8Array(64);blk[32]=0x80;blk[62]=3;const H=new Uint32Array(8);
 for(let r=1;r<it;r++){blk.set(U,0);H.set(Hi);cmp(H,blk,0);blk.set(out(H),0);H.set(Ho);cmp(H,blk,0);U=out(H);for(let i=0;i<32;i++)T[i]^=U[i];}
 return T;}
function chacha(key,nonce,data){const s=new Uint32Array(16),x=new Uint32Array(16),o=new Uint8Array(data.length);
 const le=(b,i)=>b[i]|(b[i+1]<<8)|(b[i+2]<<16)|(b[i+3]<<24);s[0]=0x61707865;s[1]=0x3320646e;s[2]=0x79622d32;s[3]=0x6b206574;
 for(let i=0;i<8;i++)s[4+i]=le(key,4*i);s[12]=0;s[13]=le(nonce,0);s[14]=le(nonce,4);s[15]=le(nonce,8);
 const R=(v,c)=>(v<<c)|(v>>>(32-c));
 const Q=(a,b,c,d)=>{x[a]+=x[b];x[d]=R(x[d]^x[a],16);x[c]+=x[d];x[b]=R(x[b]^x[c],12);x[a]+=x[b];x[d]=R(x[d]^x[a],8);x[c]+=x[d];x[b]=R(x[b]^x[c],7);};
 for(let off=0;off<data.length;off+=64){x.set(s);for(let r=0;r<10;r++){Q(0,4,8,12);Q(1,5,9,13);Q(2,6,10,14);Q(3,7,11,15);Q(0,5,10,15);Q(1,6,11,12);Q(2,7,8,13);Q(3,4,9,14);}
  for(let i=0;i<16;i++){const w=(x[i]+s[i])>>>0,j=off+4*i;if(j<data.length)o[j]=data[j]^(w&255);if(j+1<data.length)o[j+1]=data[j+1]^((w>>>8)&255);
   if(j+2<data.length)o[j+2]=data[j+2]^((w>>>16)&255);if(j+3<data.length)o[j+3]=data[j+3]^(w>>>24);}
  s[12]++;}
 return o;}
function unlock(u,pw){const r=V.U[u];if(!r)return null;const ku=pbkdf2(new TextEncoder().encode(pw),b64(r.s),V.iter);
 const [f,n,w]=r.k[0],nb=b64(n),wb=b64(w),m=new Uint8Array(nb.length+wb.length);m.set(nb,0);m.set(wb,nb.length);
 const tag=hmac(ku,m).slice(0,16),t=b64(r.t);if(tag.some((v,i)=>v!==t[i]))return null;return {f,kf:chacha(ku,nb,wb)};}
function page(f,kf){const F=V.F[f];const gz=chacha(kf,b64(F.n),b64(F.c));
 return new Response(new Blob([gz]).stream().pipeThrough(new DecompressionStream('gzip'))).text();}
function show(html){window.__jdmeHTML=html;
 window.jdmeReload=()=>{try{document.body.classList.add('switching');}catch(e){}setTimeout(()=>{document.open();document.write(window.__jdmeHTML);document.close();},40);};
 document.open();document.write(html);document.close();}
const $=id=>document.getElementById(id);
function form(){document.documentElement.className='';$('gLoad').hidden=true;$('gForm').hidden=false;try{const l=localStorage.getItem('jdme_user');if(l)$('gU').value=l;}catch(e){}($('gU').value?$('gP'):$('gU')).focus();}
let ss=null;try{ss=JSON.parse(sessionStorage.getItem('jdme_s')||'null');}catch(e){}
if(ss&&ss.f&&V.F[ss.f]){setTimeout(()=>page(ss.f,b64(ss.k)).then(show).catch(()=>{try{sessionStorage.removeItem('jdme_s');}catch(e){}form();}),20);}else form();
$('gForm').onsubmit=e=>{e.preventDefault();const u=$('gU').value.trim().toLowerCase(),p=$('gP').value;
 $('gB').disabled=true;$('gB').textContent='Opening…';$('gE').textContent='';
 setTimeout(async()=>{let R=null;try{R=unlock(u,p);}catch(err){R=null;}
  if(!R){$('gB').disabled=false;$('gB').textContent='Sign in';$('gE').textContent='The login ID or password is not right.';$('gP').select();return;}
  try{localStorage.setItem('jdme_user',u);sessionStorage.setItem('jdme_s',JSON.stringify({u,f:R.f,k:toB64(R.kf)}));}catch(e){}
  try{show(await page(R.f,R.kf));}catch(err){$('gB').disabled=false;$('gB').textContent='Sign in';$('gE').textContent='This page could not be opened. Please try again.';}},30);};
})();
</script></body></html>
"""


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--set-password"]:
        if len(a) < 3:
            sys.exit('Use: python pipeline\\lock_page.py --set-password <login> <password> [--name "Full Name"] [--page full|<manager code>]')
        opt = lambda k: a[a.index(k) + 1] if k in a else None
        set_password(a[1].strip().lower(), a[2], opt("--name"), opt("--page"))
        build()
    elif a[:1] == ["--list"]:
        for u, e in load_keys()["logins"].items():
            p = page_file(e["page"])
            print(f"{u:20} {e.get('name', ''):28} page {e['page']:10} {'ok' if p and os.path.exists(p) else 'MISSING'}")
    else:
        build()
