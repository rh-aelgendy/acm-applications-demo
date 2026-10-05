import importlib.util
from pathlib import Path
import unittest
s=importlib.util.spec_from_file_location('server',Path(__file__).parents[1]/'base/server.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Quotes(unittest.TestCase):
    def test_same_quote_after_move(self):
        import os
        os.environ['CLUSTER_NAME']='source'
        source=m.quote('regional',3)
        os.environ['CLUSTER_NAME']='destination'
        self.assertEqual(source,m.quote('regional',3))
        self.assertEqual(source['price_eur'],14)
    def test_invalid_input(self):
        for zone,weight in [('unknown',3),('local',0),('local',101)]:
            with self.assertRaises(ValueError):m.quote(zone,weight)

class HTTP(unittest.TestCase):
    def test_quote_receipt_and_invalid_request(self):
        import os, threading, json
        from urllib.request import urlopen
        from urllib.error import HTTPError
        os.environ['MODE']='engine';os.environ['CLUSTER_NAME']='test-fleet-destination';os.environ['DEPLOYMENT_LOCATION']='Edge'
        server=m.ThreadingHTTPServer(('127.0.0.1',0),m.Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            base='http://127.0.0.1:'+str(server.server_port)
            with urlopen(base+'/api/quote?zone=regional&weight=3') as response:
                data=json.load(response)
            self.assertEqual(data['cluster'],'test-fleet-destination')
            self.assertEqual(data['location'],'Edge')
            with urlopen(base+'/api/location') as response:
                self.assertEqual(json.load(response),{'cluster':'test-fleet-destination','location':'Edge'})
            self.assertEqual(data['price_eur'],14)
            with self.assertRaises(HTTPError) as failure:urlopen(base+'/api/quote?weight=-1')
            self.assertEqual(failure.exception.code,400)
            failure.exception.close()
        finally:server.shutdown();server.server_close();thread.join()

if __name__=='__main__':unittest.main()
