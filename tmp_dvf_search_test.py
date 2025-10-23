from api.price_api import PriceAPI

api = PriceAPI()
code = api._resolve_insee('Paris', '75001')
print('INSEE:', code)
recs = api._query_dvf(code, 'apartment', months=24)
print('Transactions:', len(recs))
if recs[:3]:
    print('Sample:', recs[:3])
