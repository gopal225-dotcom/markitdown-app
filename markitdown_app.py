#!/usr/bin/env python3
"""
MarkItDown — native desktop app.

A pywebview window with a JS<->Python bridge. Conversion runs in Python,
and saving uses a native macOS save dialog (single file) or folder picker
(multiple files). No browser, no Flask, proper UTF-8 handling.

Dev run:   python markitdown_app.py
Build:     see build.sh  ->  dist/MarkItDown.app and MarkItDown.dmg
"""
import os
import io
import sys
import base64

import webview

try:
    from markitdown import MarkItDown
except ImportError:
    sys.exit("MarkItDown not installed. Run: pip install 'markitdown[all]'")

md = MarkItDown(enable_plugins=False)


class Api:
    """Exposed to JavaScript as window.pywebview.api.*"""

    def __init__(self):
        self._window = None

    def set_window(self, window):
        self._window = window

    def convert(self, items):
        """
        items: list of {name, b64}  (b64 = base64 of the raw file bytes)
        Returns: {"results":[{name, md, error}], "ok_count", "err_count"}
        """
        results = []
        for it in items:
            name = it.get("name", "file")
            try:
                raw = base64.b64decode(it["b64"])
                ext = os.path.splitext(name)[1]
                out = md.convert_stream(io.BytesIO(raw), file_extension=ext)
                md_name = os.path.splitext(os.path.basename(name))[0] + ".md"
                results.append({"name": md_name, "md": out.text_content, "error": None})
            except Exception as e:  # noqa: BLE001
                results.append({"name": name, "md": None, "error": str(e)})
        ok = sum(1 for r in results if r["error"] is None)
        return {"results": results, "ok_count": ok, "err_count": len(results) - ok}

    def save_one(self, suggested_name, content):
        """Native Save-As dialog for a single .md file. Returns saved path or ''."""
        path = self._window.create_file_dialog(
            webview.SAVE_DIALOG, save_filename=suggested_name
        )
        if not path:
            return ""
        if isinstance(path, (list, tuple)):
            path = path[0]
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def save_many(self, results):
        """Native folder picker; writes all successful .md files there."""
        folder = self._window.create_file_dialog(webview.FOLDER_DIALOG)
        if not folder:
            return ""
        if isinstance(folder, (list, tuple)):
            folder = folder[0]
        written = 0
        for r in results:
            if r.get("error") is None and r.get("md") is not None:
                with open(os.path.join(folder, r["name"]), "w", encoding="utf-8") as f:
                    f.write(r["md"])
                written += 1
        return f"{written}|{folder}"


PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MarkItDown</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,900&family=Spline+Sans+Mono:wght@400;500&display=swap');
  :root{
    --ink:#13110f;--paper:#f3ead8;--paper-2:#ece0c8;
    --accent:#d6451f;--accent-2:#1f5d4c;--line:#13110f;
  }
  *{box-sizing:border-box;margin:0;padding:0}
  html,body{height:100%}
  body{
    font-family:'Spline Sans Mono',monospace;background:var(--paper);color:var(--ink);
    background-image:radial-gradient(var(--paper-2) 1px,transparent 1px);
    background-size:18px 18px;display:flex;align-items:center;justify-content:center;
    padding:30px;-webkit-user-select:none;user-select:none;
  }
  .card{
    width:100%;max-width:600px;background:var(--paper);
    border:2.5px solid var(--line);box-shadow:9px 9px 0 var(--ink);
    padding:34px 36px 26px;
  }
  .tag{
    display:inline-block;font-size:11.5px;letter-spacing:.18em;text-transform:uppercase;
    background:var(--ink);color:var(--paper);padding:5px 11px;margin-bottom:18px;
  }
  h1{font-family:'Fraunces',serif;font-weight:900;font-size:48px;line-height:.92;
    letter-spacing:-.02em;margin-bottom:10px;}
  h1 em{font-style:italic;color:var(--accent)}
  .sub{font-size:13px;line-height:1.6;max-width:46ch;margin-bottom:24px;opacity:.8}
  .drop{
    border:2.5px dashed var(--line);background:var(--paper-2);padding:42px 24px;
    text-align:center;cursor:pointer;position:relative;
    transition:transform .12s ease,background .12s ease;
  }
  .drop:hover{background:#e6d8bc}
  .drop.over{
    background:var(--accent);color:var(--paper);border-color:var(--accent);
    transform:translate(-3px,-3px);box-shadow:6px 6px 0 var(--ink);
  }
  .drop .big{font-family:'Fraunces',serif;font-weight:600;font-size:21px;margin-bottom:6px}
  .drop .small{font-size:12px;opacity:.75}
  .drop.over .small{opacity:.9}
  input[type=file]{display:none}
  .formats{margin-top:15px;font-size:10.5px;letter-spacing:.05em;opacity:.6;line-height:1.7}
  .list{margin-top:20px;display:flex;flex-direction:column;gap:8px}
  .row{display:flex;align-items:center;gap:10px;font-size:12.5px;
    border:2px solid var(--line);padding:9px 12px;background:var(--paper)}
  .row .dot{width:9px;height:9px;background:var(--accent-2);flex:0 0 auto}
  .row .nm{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .row .x{cursor:pointer;font-weight:600;opacity:.5}
  .row .x:hover{opacity:1;color:var(--accent)}
  .go{margin-top:22px;width:100%;font-family:'Fraunces',serif;font-weight:600;font-size:18px;
    background:var(--ink);color:var(--paper);border:2.5px solid var(--ink);padding:14px;
    cursor:pointer;transition:transform .12s ease,box-shadow .12s ease}
  .go:hover:not(:disabled){transform:translate(-3px,-3px);box-shadow:6px 6px 0 var(--accent)}
  .go:disabled{opacity:.35;cursor:not-allowed}
  .status{margin-top:14px;font-size:12px;min-height:18px;line-height:1.5}
  .status.err{color:var(--accent)}
  .status.ok{color:var(--accent-2)}
  .spin{display:inline-block;animation:sp 1s linear infinite}
  @keyframes sp{to{transform:rotate(360deg)}}
</style>
</head>
<body>
  <div class="card">
    <span class="tag">MarkItDown · Local</span>
    <h1>Drop files,<br>get <em>Markdown</em>.</h1>
    <p class="sub">PDF, Word, Excel, PowerPoint, images &amp; more → clean Markdown.
      Runs entirely on your Mac.</p>
    <div class="drop" id="drop">
      <div class="big">Drag &amp; drop files here</div>
      <div class="small">or click to browse</div>
    </div>
    <input type="file" id="file" multiple>
    <div class="formats">PDF · DOCX · XLSX · PPTX · HTML · CSV · JSON · XML · IMAGES · EPUB · ZIP</div>
    <div class="list" id="list"></div>
    <button class="go" id="go" disabled>Convert &amp; Save</button>
    <div class="status" id="status"></div>
  </div>
<script>
  const drop=document.getElementById('drop'),input=document.getElementById('file'),
        listEl=document.getElementById('list'),go=document.getElementById('go'),
        status=document.getElementById('status');
  let files=[];
  function render(){
    listEl.innerHTML='';
    files.forEach((f,i)=>{
      const r=document.createElement('div');r.className='row';
      r.innerHTML='<span class="dot"></span><span class="nm"></span><span class="x">remove</span>';
      r.querySelector('.nm').textContent=f.name;
      r.querySelector('.x').onclick=()=>{files.splice(i,1);render();};
      listEl.appendChild(r);
    });
    go.disabled=!files.length; if(files.length) status.textContent='';
  }
  const add=fl=>{files=files.concat(Array.from(fl));render();};
  drop.onclick=()=>input.click();
  input.onchange=e=>add(e.target.files);
  ['dragenter','dragover'].forEach(ev=>drop.addEventListener(ev,e=>{e.preventDefault();drop.classList.add('over');}));
  ['dragleave','drop'].forEach(ev=>drop.addEventListener(ev,e=>{e.preventDefault();drop.classList.remove('over');}));
  drop.addEventListener('drop',e=>{if(e.dataTransfer.files.length)add(e.dataTransfer.files);});

  const toB64=file=>new Promise((res,rej)=>{
    const r=new FileReader();
    r.onload=()=>res(r.result.split(',')[1]);   // strip data: prefix
    r.onerror=rej;
    r.readAsDataURL(file);
  });

  go.onclick=async()=>{
    if(!files.length)return;
    go.disabled=true;status.className='status';
    status.innerHTML='<span class="spin">◍</span> Converting '+files.length+' file(s)…';
    try{
      const items=[];
      for(const f of files){ items.push({name:f.name, b64:await toB64(f)}); }
      const out=await window.pywebview.api.convert(items);

      if(out.ok_count===1 && out.err_count===0){
        const r=out.results.find(x=>x.error===null);
        const path=await window.pywebview.api.save_one(r.name, r.md);
        status.className='status '+(path?'ok':'');
        status.textContent=path?('✓ Saved: '+path):'Save cancelled.';
      }else if(out.ok_count>0){
        const ret=await window.pywebview.api.save_many(out.results);
        if(!ret){status.textContent='Save cancelled.';}
        else{
          const [n,folder]=ret.split('|');
          let msg='✓ Saved '+n+' file(s) to '+folder;
          if(out.err_count>0) msg+='  ('+out.err_count+' failed)';
          status.className='status ok';status.textContent=msg;
        }
      }else{
        const first=out.results.find(x=>x.error);
        status.className='status err';
        status.textContent='✕ '+(first?first.error:'Conversion failed');
      }
    }catch(err){
      status.className='status err';status.textContent='✕ '+(err.message||err);
    }finally{
      go.disabled=!files.length;
    }
  };
</script>
</body>
</html>"""


def main():
    api = Api()
    window = webview.create_window(
        "MarkItDown", html=PAGE, js_api=api,
        width=680, height=720, min_size=(560, 600),
    )
    api.set_window(window)
    webview.start()


if __name__ == "__main__":
    main()
