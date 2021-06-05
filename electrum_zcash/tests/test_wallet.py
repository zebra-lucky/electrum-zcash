import shutil
import tempfile
import sys
import os
import json
from decimal import Decimal
import time
from io import StringIO
import asyncio

from electrum_zcash.storage import WalletStorage
from electrum_zcash.wallet_db import FINAL_SEED_VERSION
from electrum_zcash.wallet import (Abstract_Wallet, Standard_Wallet, create_new_wallet,
                             restore_wallet_from_text, Imported_Wallet, Wallet)
from electrum_zcash.exchange_rate import ExchangeBase, FxThread
from electrum_zcash.util import TxMinedInfo, InvalidPassword
from electrum_zcash.bitcoin import COIN
from electrum_zcash.wallet_db import WalletDB
from electrum_zcash.simple_config import SimpleConfig
from electrum_zcash import util

from . import ElectrumTestCase


class FakeSynchronizer(object):

    def __init__(self):
        self.store = []

    def add(self, address):
        self.store.append(address)


class WalletTestCase(ElectrumTestCase):

    def setUp(self):
        super(WalletTestCase, self).setUp()
        self.user_dir = tempfile.mkdtemp()
        self.config = SimpleConfig({'electrum_path': self.user_dir})

        self.wallet_path = os.path.join(self.user_dir, "somewallet")

        self._saved_stdout = sys.stdout
        self._stdout_buffer = StringIO()
        sys.stdout = self._stdout_buffer

    def tearDown(self):
        super(WalletTestCase, self).tearDown()
        shutil.rmtree(self.user_dir)
        # Restore the "real" stdout
        sys.stdout = self._saved_stdout


class TestWalletStorage(WalletTestCase):

    def test_read_dictionary_from_file(self):

        some_dict = {"a":"b", "c":"d"}
        contents = json.dumps(some_dict)
        with open(self.wallet_path, "w") as f:
            contents = f.write(contents)

        storage = WalletStorage(self.wallet_path)
        db = WalletDB(storage.read(), manual_upgrades=True)
        self.assertEqual("b", db.get("a"))
        self.assertEqual("d", db.get("c"))

    def test_write_dictionary_to_file(self):

        storage = WalletStorage(self.wallet_path)
        db = WalletDB('', manual_upgrades=True)

        some_dict = {
            u"a": u"b",
            u"c": u"d",
            u"seed_version": FINAL_SEED_VERSION}

        for key, value in some_dict.items():
            db.put(key, value)
        db.write(storage)

        with open(self.wallet_path, "r") as f:
            contents = f.read()
        d = json.loads(contents)
        for key, value in some_dict.items():
            self.assertEqual(d[key], value)

class FakeExchange(ExchangeBase):
    def __init__(self, rate):
        super().__init__(lambda self: None, lambda self: None)
        self.quotes = {'TEST': rate}

class FakeFxThread:
    def __init__(self, exchange):
        self.exchange = exchange
        self.ccy = 'TEST'

    remove_thousands_separator = staticmethod(FxThread.remove_thousands_separator)
    timestamp_rate = FxThread.timestamp_rate
    ccy_amount_str = FxThread.ccy_amount_str
    history_rate = FxThread.history_rate

class FakeWallet:
    def __init__(self, fiat_value):
        super().__init__()
        self.fiat_value = fiat_value
        self.db = WalletDB("{}", manual_upgrades=True)
        self.db.transactions = self.db.verified_tx = {'abc':'Tx'}

    def get_tx_height(self, txid):
        # because we use a current timestamp, and history is empty,
        # FxThread.history_rate will use spot prices
        return TxMinedInfo(height=10, conf=10, timestamp=int(time.time()), header_hash='def')

    default_fiat_value = Abstract_Wallet.default_fiat_value
    price_at_timestamp = Abstract_Wallet.price_at_timestamp
    class storage:
        put = lambda self, x: None

txid = 'abc'
ccy = 'TEST'

class TestFiat(ElectrumTestCase):
    def setUp(self):
        super().setUp()
        self.value_sat = COIN
        self.fiat_value = {}
        self.wallet = FakeWallet(fiat_value=self.fiat_value)
        self.fx = FakeFxThread(FakeExchange(Decimal('1000.001')))
        default_fiat = Abstract_Wallet.default_fiat_value(self.wallet, txid, self.fx, self.value_sat)
        self.assertEqual(Decimal('1000.001'), default_fiat)
        self.assertEqual('1,000.00', self.fx.ccy_amount_str(default_fiat, commas=True))

    def test_save_fiat_and_reset(self):
        self.assertEqual(False, Abstract_Wallet.set_fiat_value(self.wallet, txid, ccy, '1000.01', self.fx, self.value_sat))
        saved = self.fiat_value[ccy][txid]
        self.assertEqual('1,000.01', self.fx.ccy_amount_str(Decimal(saved), commas=True))
        self.assertEqual(True,       Abstract_Wallet.set_fiat_value(self.wallet, txid, ccy, '', self.fx, self.value_sat))
        self.assertNotIn(txid, self.fiat_value[ccy])
        # even though we are not setting it to the exact fiat value according to the exchange rate, precision is truncated away
        self.assertEqual(True, Abstract_Wallet.set_fiat_value(self.wallet, txid, ccy, '1,000.002', self.fx, self.value_sat))

    def test_too_high_precision_value_resets_with_no_saved_value(self):
        self.assertEqual(True, Abstract_Wallet.set_fiat_value(self.wallet, txid, ccy, '1,000.001', self.fx, self.value_sat))

    def test_empty_resets(self):
        self.assertEqual(True, Abstract_Wallet.set_fiat_value(self.wallet, txid, ccy, '', self.fx, self.value_sat))
        self.assertNotIn(ccy, self.fiat_value)

    def test_save_garbage(self):
        self.assertEqual(False, Abstract_Wallet.set_fiat_value(self.wallet, txid, ccy, 'garbage', self.fx, self.value_sat))
        self.assertNotIn(ccy, self.fiat_value)


class TestCreateRestoreWallet(WalletTestCase):

    def test_create_new_wallet(self):
        passphrase = 'mypassphrase'
        password = 'mypassword'
        encrypt_file = True
        d = create_new_wallet(path=self.wallet_path,
                              passphrase=passphrase,
                              password=password,
                              encrypt_file=encrypt_file,
                              gap_limit=1,
                              config=self.config)
        wallet = d['wallet']  # type: Standard_Wallet
        wallet.check_password(password)
        self.assertEqual(passphrase, wallet.keystore.get_passphrase(password))
        self.assertEqual(d['seed'], wallet.keystore.get_seed(password))
        self.assertEqual(encrypt_file, wallet.storage.is_encrypted())

    def test_restore_wallet_from_text_mnemonic(self):
        text = 'hint shock chair puzzle shock traffic drastic note dinosaur mention suggest sweet'
        passphrase = 'mypassphrase'
        password = 'mypassword'
        encrypt_file = True
        d = restore_wallet_from_text(text,
                                     path=self.wallet_path,
                                     passphrase=passphrase,
                                     password=password,
                                     encrypt_file=encrypt_file,
                                     gap_limit=1,
                                     config=self.config)
        wallet = d['wallet']  # type: Standard_Wallet
        self.assertEqual(passphrase, wallet.keystore.get_passphrase(password))
        self.assertEqual(text, wallet.keystore.get_seed(password))
        self.assertEqual(encrypt_file, wallet.storage.is_encrypted())
        self.assertEqual('t1LQ4AarpUGURKZ2gcBjmgFVobEdBJQY49R', wallet.get_receiving_addresses()[0])

    def test_restore_wallet_from_text_xpub(self):
        text = 'xpub6ASuArnXKPbfEwhqN6e3mwBcDTgzisQN1wXN9BJcM47sSikHjJf3UFHKkNAWbWMiGj7Wf5uMash7SyYq527Hqck2AxYysAA7xmALppuCkwQ'
        d = restore_wallet_from_text(text, path=self.wallet_path, gap_limit=1, config=self.config)
        wallet = d['wallet']  # type: Standard_Wallet
        self.assertEqual(text, wallet.keystore.get_master_public_key())
        self.assertEqual('t1UaodrrMGJS83dpqyFPcX4bP7SB2zhiWKX', wallet.get_receiving_addresses()[0])

    def test_restore_wallet_from_text_xkey_that_is_also_a_valid_electrum_seed_by_chance(self):
        text = 'xprv9s21ZrQH143K39BUkM2iuppjFpkJ37KUqQAaDvvTzeCSDCtpqM1TsN47vmuUqyJqEVJUmFBDo55dsKwhzYD6sPTecP2JeNbYoia7hzf6Jzt'
        d = restore_wallet_from_text(text, path=self.wallet_path, gap_limit=1, config=self.config)
        wallet = d['wallet']  # type: Standard_Wallet
        self.assertEqual(text, wallet.keystore.get_master_private_key(password=None))
        self.assertEqual('t1SCgYCZ8LTwpZpLVp4hLYXwXJV757NfVyz', wallet.get_receiving_addresses()[0])

    def test_restore_wallet_from_text_xprv(self):
        text = 'xprv9wTYmMFdV23N2TdNG573QoEsfRrWKQgWeibmLntzniatZvR9BmLnvSxqu53Kw1UmYPxLgboyZQaXwTCg8MSY3H2EU4pWcQDnRnrVA1xe8fs'
        d = restore_wallet_from_text(text, path=self.wallet_path, gap_limit=1, config=self.config)
        wallet = d['wallet']  # type: Standard_Wallet
        self.assertEqual(text, wallet.keystore.get_master_private_key(password=None))
        self.assertEqual('t1UaodrrMGJS83dpqyFPcX4bP7SB2zhiWKX', wallet.get_receiving_addresses()[0])

    def test_restore_wallet_from_text_addresses(self):
        text = 't1LvhooU7zQuqEtjZZN83EL8QSBUkd8WkHR t1M4tYuzKx46ARb7hDcdnMAjkx8Acdrbd9Z'
        d = restore_wallet_from_text(text, path=self.wallet_path, config=self.config)
        wallet = d['wallet']  # type: Imported_Wallet
        self.assertEqual('t1LvhooU7zQuqEtjZZN83EL8QSBUkd8WkHR', wallet.get_receiving_addresses()[0])
        self.assertEqual(2, len(wallet.get_receiving_addresses()))
        # also test addr deletion
        wallet.delete_address('t1M4tYuzKx46ARb7hDcdnMAjkx8Acdrbd9Z')
        self.assertEqual(1, len(wallet.get_receiving_addresses()))

    def test_restore_wallet_from_text_privkeys(self):
        text = 'p2pkh:L2tCtZNQ2kHhNPMYnnxGaqzBfP3q9qkF8GLGAaqt83DYQiHm4cH6 p2pkh:KziELqRDg4EyiUE2uTc4FdKV1i9oPb7oaoXqmn3y1VJD4hNnJ2nG'
        d = restore_wallet_from_text(text, path=self.wallet_path, config=self.config)
        wallet = d['wallet']  # type: Imported_Wallet
        addr0 = wallet.get_receiving_addresses()[0]
        self.assertEqual('t1KtqVs7jkuRqd7CTh1ZeE4QS61Br7vW4C8', addr0)
        self.assertEqual('p2pkh:KziELqRDg4EyiUE2uTc4FdKV1i9oPb7oaoXqmn3y1VJD4hNnJ2nG',
                         wallet.export_private_key(addr0, password=None))
        self.assertEqual(2, len(wallet.get_receiving_addresses()))
        # also test addr deletion
        wallet.delete_address('t1UaodrrMGJS83dpqyFPcX4bP7SB2zhiWKX')
        self.assertEqual(1, len(wallet.get_receiving_addresses()))


class TestWalletPassword(WalletTestCase):

    def setUp(self):
        super().setUp()
        self.asyncio_loop, self._stop_loop, self._loop_thread = util.create_and_start_event_loop()

    def tearDown(self):
        super().tearDown()
        self.asyncio_loop.call_soon_threadsafe(self._stop_loop.set_result, 1)
        self._loop_thread.join(timeout=1)

    def test_update_password_of_imported_wallet(self):
        wallet_str = '{"addr_history":{"t1KxfKCSdEQsnY4geXEmHi4zYeFCjFBq9Vn":[],"t1N5aE1koddeuH3ubZQcvP6Ac39QLr5HZ9T":[],"t1XqFtMbqGC3Yv6zbj6SzKArJnzU1e2zZxM":[]},"addresses":{"change":[],"receiving":["t1KxfKCSdEQsnY4geXEmHi4zYeFCjFBq9Vn","t1XqFtMbqGC3Yv6zbj6SzKArJnzU1e2zZxM","t1N5aE1koddeuH3ubZQcvP6Ac39QLr5HZ9T"]},"keystore":{"keypairs":{"0344b1588589958b0bcab03435061539e9bcf54677c104904044e4f8901f4ebdf5":"L2sED74axVXC4H8szBJ4rQJrkfem7UMc6usLCPUoEWxDCFGUaGUM","0389508c13999d08ffae0f434a085f4185922d64765c0bff2f66e36ad7f745cc5f":"L3Gi6EQLvYw8gEEUckmqawkevfj9s8hxoQDFveQJGZHTfyWnbk1U","04575f52b82f159fa649d2a4c353eb7435f30206f0a6cb9674fbd659f45082c37d559ffd19bea9c0d3b7dcc07a7b79f4cffb76026d5d4dff35341efe99056e22d2":"5JyVyXU1LiRXATvRTQvR9Kp8Rx1X84j2x49iGkjSsXipydtByUq"},"type":"imported"},"pruned_txo":{},"seed_version":13,"stored_height":-1,"transactions":{},"tx_fees":{},"txi":{},"txo":{},"use_encryption":false,"verified_tx3":{},"wallet_type":"standard","winpos-qt":[100,100,840,405]}'
        db = WalletDB(wallet_str, manual_upgrades=False)
        storage = WalletStorage(self.wallet_path)
        wallet = Wallet(db, storage, config=self.config)

        wallet.check_password(None)

        wallet.update_password(None, "1234")

        with self.assertRaises(InvalidPassword):
            wallet.check_password(None)
        with self.assertRaises(InvalidPassword):
            wallet.check_password("wrong password")
        wallet.check_password("1234")

    def test_update_password_of_standard_wallet(self):
        wallet_str = '''{"addr_history":{"t1K6oh6QT515QVxDT3qXvwMHpzfPm6cBNRi":[],"t1Kb24NfXZQ8iUa7FZHfD6ptCaK1kxZSfFT":[],"t1LA42A5ebDf388JtBXv2gibYfaoFB4NuCN":[],"t1Lcs9qhHHADiJcFWRkq119jJAimcfLJj3M":[],"t1MLG4B8rFdK3V5WxGCXmuyoCux2C4TYL6o":[],"t1MZNCHxd7SZb9aZXEs7AVGSWhwgjPoyHKy":[],"t1N7sudLZrCgcSmi6sZx3zQvarhY9hooRuc":[],"t1Qfv1H4J11Zh2rnmG6yH4HK14Ge6diB1xf":[],"t1RZycn9hxkQ1yjLvY64Z6dFPvUYsyL4N4h":[],"t1RekPbNKi66nsLfxKd2MNeenxgPxYosVQe":[],"t1SSk8u5NdJzyBqzcZvXoctV5Zc3Vm9JWgr":[],"t1SrejMeUovTdR4B1YQ1L1rH8DycCgGvXw7":[],"t1Sv8T7LUPFRzNZp1v3hzQZHGmokQ7WJfh9":[],"t1J5Nhb4A9goHkNkYCF7nCj94n2aowBe767":[],"t1WnRi2hcZJ7bCPgpfvYnDSzf2gMHYgj61X":[],"t1WwagmnSnq7dW2aTDce1uH8G6bkYese4ea":[],"t1ZKpT5AdaUiBApE5CoJxayUCYqotAuVAbX":[],"t1ZPSh9sq9EEReXGa3L1vUE4Jn4ZsGZpYeU":[],"t1ZaNqHFaDQQRyKgk6E7UhmEYacaWaRKBNg":[],"t1ax4TopTgGSHpoFq2jZ1mpKwGugwNuA9dq":[],"t1bPaTLA8H2eq47XWmvNR3jWFQn1jxboBjQ":[],"t1cGtxxPBNo4m6zLDRK7ry2FXbyihKqPe51":[],"t1cgZa12AJCUQXNK7uNehvQM9QmHzqXYo9r":[],"t1ci6EiwmnvLWqEzmW33StfFyQgvxXwxDWM":[],"t1eshyYrgcRtCfo66jvcdJ94CtpfgqWB1bA":[],"t1gdjJX88Sd1SF3TDoCbvwpMn6j1nWhjo23":[]},"addresses":{"change":["t1ZaNqHFaDQQRyKgk6E7UhmEYacaWaRKBNg","t1ZKpT5AdaUiBApE5CoJxayUCYqotAuVAbX","t1N7sudLZrCgcSmi6sZx3zQvarhY9hooRuc","t1Sv8T7LUPFRzNZp1v3hzQZHGmokQ7WJfh9","t1SrejMeUovTdR4B1YQ1L1rH8DycCgGvXw7","t1bPaTLA8H2eq47XWmvNR3jWFQn1jxboBjQ"],"receiving":["t1MZNCHxd7SZb9aZXEs7AVGSWhwgjPoyHKy","t1LA42A5ebDf388JtBXv2gibYfaoFB4NuCN","t1SSk8u5NdJzyBqzcZvXoctV5Zc3Vm9JWgr","t1ax4TopTgGSHpoFq2jZ1mpKwGugwNuA9dq","t1gdjJX88Sd1SF3TDoCbvwpMn6j1nWhjo23","t1Lcs9qhHHADiJcFWRkq119jJAimcfLJj3M","t1cGtxxPBNo4m6zLDRK7ry2FXbyihKqPe51","t1K6oh6QT515QVxDT3qXvwMHpzfPm6cBNRi","t1Kb24NfXZQ8iUa7FZHfD6ptCaK1kxZSfFT","t1MLG4B8rFdK3V5WxGCXmuyoCux2C4TYL6o","t1ci6EiwmnvLWqEzmW33StfFyQgvxXwxDWM","t1Qfv1H4J11Zh2rnmG6yH4HK14Ge6diB1xf","t1WwagmnSnq7dW2aTDce1uH8G6bkYese4ea","t1RZycn9hxkQ1yjLvY64Z6dFPvUYsyL4N4h","t1cgZa12AJCUQXNK7uNehvQM9QmHzqXYo9r","t1RekPbNKi66nsLfxKd2MNeenxgPxYosVQe","t1J5Nhb4A9goHkNkYCF7nCj94n2aowBe767","t1WnRi2hcZJ7bCPgpfvYnDSzf2gMHYgj61X","t1ZPSh9sq9EEReXGa3L1vUE4Jn4ZsGZpYeU","t1eshyYrgcRtCfo66jvcdJ94CtpfgqWB1bA"]},"keystore":{"seed":"cereal wise two govern top pet frog nut rule sketch bundle logic","type":"bip32","xprv":"xprv9s21ZrQH143K29XjRjUs6MnDB9wXjXbJP2kG1fnRk8zjdDYWqVkQYUqaDtgZp5zPSrH5PZQJs8sU25HrUgT1WdgsPU8GbifKurtMYg37d4v","xpub":"xpub661MyMwAqRbcEdcCXm1sTViwjBn28zK9kFfrp4C3JUXiW1sfP34f6HA45B9yr7EH5XGzWuTfMTdqpt9XPrVQVUdgiYb5NW9m8ij1FSZgGBF"},"pruned_txo":{},"seed_type":"standard","seed_version":13,"stored_height":-1,"transactions":{},"tx_fees":{},"txi":{},"txo":{},"use_encryption":false,"verified_tx3":{},"wallet_type":"standard","winpos-qt":[619,310,840,405]}'''
        db = WalletDB(wallet_str, manual_upgrades=False)
        storage = WalletStorage(self.wallet_path)
        wallet = Wallet(db, storage, config=self.config)

        wallet.check_password(None)

        wallet.update_password(None, "1234")
        with self.assertRaises(InvalidPassword):
            wallet.check_password(None)
        with self.assertRaises(InvalidPassword):
            wallet.check_password("wrong password")
        wallet.check_password("1234")

    def test_update_password_with_app_restarts(self):
        wallet_str = '{"addr_history":{"t1KxfKCSdEQsnY4geXEmHi4zYeFCjFBq9Vn":[],"t1N5aE1koddeuH3ubZQcvP6Ac39QLr5HZ9T":[],"t1XqFtMbqGC3Yv6zbj6SzKArJnzU1e2zZxM":[]},"addresses":{"change":[],"receiving":["t1KxfKCSdEQsnY4geXEmHi4zYeFCjFBq9Vn","t1XqFtMbqGC3Yv6zbj6SzKArJnzU1e2zZxM","t1N5aE1koddeuH3ubZQcvP6Ac39QLr5HZ9T"]},"keystore":{"keypairs":{"0344b1588589958b0bcab03435061539e9bcf54677c104904044e4f8901f4ebdf5":"L2sED74axVXC4H8szBJ4rQJrkfem7UMc6usLCPUoEWxDCFGUaGUM","0389508c13999d08ffae0f434a085f4185922d64765c0bff2f66e36ad7f745cc5f":"L3Gi6EQLvYw8gEEUckmqawkevfj9s8hxoQDFveQJGZHTfyWnbk1U","04575f52b82f159fa649d2a4c353eb7435f30206f0a6cb9674fbd659f45082c37d559ffd19bea9c0d3b7dcc07a7b79f4cffb76026d5d4dff35341efe99056e22d2":"5JyVyXU1LiRXATvRTQvR9Kp8Rx1X84j2x49iGkjSsXipydtByUq"},"type":"imported"},"pruned_txo":{},"seed_version":13,"stored_height":-1,"transactions":{},"tx_fees":{},"txi":{},"txo":{},"use_encryption":false,"verified_tx3":{},"wallet_type":"standard","winpos-qt":[100,100,840,405]}'
        db = WalletDB(wallet_str, manual_upgrades=False)
        storage = WalletStorage(self.wallet_path)
        wallet = Wallet(db, storage, config=self.config)
        asyncio.run_coroutine_threadsafe(wallet.stop(), self.asyncio_loop).result()

        storage = WalletStorage(self.wallet_path)
        # if storage.is_encrypted():
        #     storage.decrypt(password)
        db = WalletDB(storage.read(), manual_upgrades=False)
        wallet = Wallet(db, storage, config=self.config)

        wallet.check_password(None)

        wallet.update_password(None, "1234")
        with self.assertRaises(InvalidPassword):
            wallet.check_password(None)
        with self.assertRaises(InvalidPassword):
            wallet.check_password("wrong password")
        wallet.check_password("1234")
