import json
import os
from pathlib import Path
import subprocess
import sys
root=Path(__file__).resolve().parents[2]
invalid=root/'results/local/invalid-bundle.json'
invalid.write_text('{"meta":{"data_mode":"real"}}',encoding='utf-8')
empty=root/'results/local/empty-synthetic-bundle.json'
fixture=json.loads((root/'tests/fixtures/demo_bundle.json').read_text(encoding='utf-8'))
for rec in fixture['recommendations']:
    if rec['user_id']=='U_demo_new': rec['items']=[]
empty.write_text(json.dumps(fixture,ensure_ascii=False),encoding='utf-8')
configs={'real':(8513,root/'artifacts/demo/v1/demo_bundle.json'),
         'fixture':(8514,root/'tests/fixtures/demo_bundle.json'),
         'invalid':(8515,invalid), 'empty':(8516,empty)}
label=sys.argv[1]
port,bundle=configs[label]
env=os.environ|{'PYTHONPATH':str(root/'src'),'RECSYSEDU_BUNDLE':str(bundle)}
log=(root/f'results/local/streamlit-{label}.log').open('w',encoding='utf-8')
p=subprocess.Popen([sys.executable,'-m','streamlit','run','app/streamlit_app.py','--server.address','127.0.0.1','--server.port',str(port),'--server.headless','true'],cwd=root,env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
print(json.dumps({'label':label,'pid':p.pid,'port':port}))
