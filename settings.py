import os


class settings(object):
    phoneNumber = '+375291111111'
    apiId = '42ea2203-a777-a3c4-1d99-3fef302c7f92'
    trackFolder = os.path.join(os.path.expanduser('~/www/python/sms/tracks/'))

    items = [
        ['CJ420541567US', 'Longboard deck', 'international', 'translit'],
        #['RQ154037942SG', 'Something', 'local'],
    ]
    # 'CJ420541567US' - your tracking code
    # 'Longboard deck' - something to just identify your item
    # 'internatoinal' - type of shipping, must be 'international' or 'local'
    # 'translit' - what to do if message is too long (more than 70 cyrillic symbols), must be 'translit' or 'split'
