import importlib.util, pathlib, unittest, uuid
spec=importlib.util.spec_from_file_location('orders_api',pathlib.Path(__file__).parents[1]/'base/api.py')
api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
class OrdersTests(unittest.TestCase):
    def payload(self,items):return {'requestId':str(uuid.uuid4()),'items':items}
    def test_server_calculates_total(self):
        _,items,total=api.normalize(self.payload([{'id':'coffee','quantity':2},{'id':'mug','quantity':1}]))
        self.assertEqual(total,6000);self.assertEqual(items[0]['unitPrice'],1800)
    def test_rejects_price_override(self):
        with self.assertRaises(ValueError):api.normalize(self.payload([{'id':'coffee','quantity':1,'price':1}]))
    def test_rejects_invalid_quantities(self):
        for qty in [0,-1,11,True,1.5,'2']:
            with self.subTest(qty=qty),self.assertRaises(ValueError):api.normalize(self.payload([{'id':'coffee','quantity':qty}]))
    def test_rejects_unknown_and_duplicate_products(self):
        for items in [[{'id':'other','quantity':1}],[{'id':'coffee','quantity':1}]*2]:
            with self.assertRaises(ValueError):api.normalize(self.payload(items))
    def test_requires_uuid(self):
        with self.assertRaises(ValueError):api.normalize({'requestId':'invalid','items':[{'id':'mug','quantity':1}]})
    def test_requires_nonempty_basket(self):
        with self.assertRaises(ValueError):api.normalize(self.payload([]))
if __name__=='__main__':unittest.main()
