from api.price_api import PriceAPI

api = PriceAPI()
print('Testing DVF analyze-only for Paris 75001...')
print(api.get_local_prices('Paris', postal_code='75001', property_type='apartment'))
print('Testing DVF analyze-only for Lyon 69001...')
print(api.get_local_prices('Lyon', postal_code='69001', property_type='apartment'))
