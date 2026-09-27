"""Synthetic order API. Database is the source of truth; never log credentials."""
import json, os, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import pg8000.dbapi

PRODUCTS=[{'id':'coffee','name':'Everyday roast','description':'A balanced, small-batch blend.','price':1800,'category':'Coffee','icon':'☕'},
{'id':'pour-over','name':'Slow morning kit','description':'Make a ritual out of the everyday.','price':4200,'category':'Equipment','icon':'◒'},
{'id':'mug','name':'Studio ceramic mug','description':'Hand-finished. Made to keep.','price':2400,'category':'Home','icon':'◡'},
{'id':'tea','name':'Garden green tea','description':'Bright leaves. A gentler start.','price':1600,'category':'Tea','icon':'❋'}]

def connection():
    return pg8000.dbapi.connect(host=os.getenv('DB_HOST','orders-db'),database=os.environ['DB_NAME'],user=os.environ['DB_USER'],password=os.environ['DB_PASSWORD'],timeout=5)

def normalize(data):
    if not isinstance(data,dict) or set(data)!={'items','requestId'}:raise ValueError('Provide items and requestId')
    request_id=str(uuid.UUID(data['requestId']))
    items=data['items']
    if not isinstance(items,list) or not 1<=len(items)<=4:raise ValueError('Choose 1 to 4 products')
    catalog={p['id']:p for p in PRODUCTS};seen=set();result=[]
    for item in items:
        if not isinstance(item,dict) or set(item)!={'id','quantity'}:raise ValueError('Invalid item')
        key=item['id'];qty=item['quantity']
        if not isinstance(key,str) or key not in catalog or key in seen:raise ValueError('Unknown or duplicate product')
        if type(qty) is not int or not 1<=qty<=10:raise ValueError('Quantity must be 1 to 10')
        seen.add(key);p=catalog[key];result.append({'id':key,'name':p['name'],'quantity':qty,'unitPrice':p['price']})
    return request_id,result,sum(p['unitPrice']*p['quantity'] for p in result)

def row_order(row):return {'id':str(row[0]),'createdAt':row[1].isoformat(),'items':json.loads(row[2]),'total':row[3],'status':'Confirmed'}

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def reply(self,status,data):
        b=json.dumps(data).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(b)
    def do_GET(self):
        path=self.path.split('?')[0]
        if path=='/healthz':return self.reply(200,{'alive':True})
        if path=='/api/products':return self.reply(200,{'products':PRODUCTS,'currency':'EUR'})
        if path not in ['/readyz','/api/status','/api/orders']:return self.reply(404,{'error':'Not found'})
        conn=None
        try:
            conn=connection();cur=conn.cursor()
            cur.execute('CREATE TABLE IF NOT EXISTS orders (id UUID PRIMARY KEY, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), items TEXT NOT NULL, total INTEGER NOT NULL CHECK(total>0))');conn.commit()
            if path=='/api/orders':
                cur.execute('SELECT id,created_at,items,total FROM orders ORDER BY created_at DESC LIMIT 50');return self.reply(200,{'orders':[row_order(row) for row in cur.fetchall()]})
            cur.execute('SELECT COUNT(*),COALESCE(SUM(total),0) FROM orders');count,total=cur.fetchone()
            self.reply(200,{'database':'Connected','orders':count,'total':total,'apiPod':os.getenv('HOSTNAME','api'),'storage':'Persistent volume','version':'1.0.0'})
        except Exception:
            self.reply(503,{'error':'Database is not ready. Please retry shortly.'})
        finally:
            if conn:conn.close()
    def do_POST(self):
        if self.path!='/api/orders':return self.reply(404,{'error':'Not found'})
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=4096:raise ValueError('Invalid request size')
            request_id,items,total=normalize(json.loads(self.rfile.read(size)))
        except (ValueError,TypeError,KeyError,AttributeError):return self.reply(400,{'error':'Choose valid products and quantities; a UUID requestId is required.'})
        conn=None
        try:
            conn=connection();cur=conn.cursor()
            cur.execute('INSERT INTO orders (id,items,total) VALUES (%s,%s,%s) ON CONFLICT (id) DO NOTHING',(request_id,json.dumps(items),total));conn.commit()
            cur.execute('SELECT id,created_at,items,total FROM orders WHERE id=%s',(request_id,));order=row_order(cur.fetchone())
            if order['items']!=items:return self.reply(409,{'error':'Request ID already used for another basket'})
            self.reply(201,{'order':order})
        except Exception:self.reply(503,{'error':'Could not confirm this order. Retry with the same request ID.'})
        finally:
            if conn:conn.close()

if __name__=='__main__':ThreadingHTTPServer(('0.0.0.0',8080),Handler).serve_forever()
