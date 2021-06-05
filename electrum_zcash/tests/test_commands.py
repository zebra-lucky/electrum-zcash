import unittest
from unittest import mock
from decimal import Decimal

from electrum_zcash.util import create_and_start_event_loop
from electrum_zcash.commands import Commands, eval_bool
from electrum_zcash import storage, wallet
from electrum_zcash.wallet import restore_wallet_from_text
from electrum_zcash.simple_config import SimpleConfig
from electrum_zcash.transaction import tx_from_any

from . import TestCaseForTestnet, ElectrumTestCase


class TestCommands(ElectrumTestCase):

    def setUp(self):
        super().setUp()
        self.asyncio_loop, self._stop_loop, self._loop_thread = create_and_start_event_loop()
        self.config = SimpleConfig({'electrum_path': self.electrum_path})

    def tearDown(self):
        super().tearDown()
        self.asyncio_loop.call_soon_threadsafe(self._stop_loop.set_result, 1)
        self._loop_thread.join(timeout=1)

    def test_setconfig_non_auth_number(self):
        self.assertEqual(7777, Commands._setconfig_normalize_value('rpcport', "7777"))
        self.assertEqual(7777, Commands._setconfig_normalize_value('rpcport', '7777'))
        self.assertAlmostEqual(Decimal(2.3), Commands._setconfig_normalize_value('somekey', '2.3'))

    def test_setconfig_non_auth_number_as_string(self):
        self.assertEqual("7777", Commands._setconfig_normalize_value('somekey', "'7777'"))

    def test_setconfig_non_auth_boolean(self):
        self.assertEqual(True, Commands._setconfig_normalize_value('show_console_tab', "true"))
        self.assertEqual(True, Commands._setconfig_normalize_value('show_console_tab', "True"))

    def test_setconfig_non_auth_list(self):
        self.assertEqual(['file:///var/www/', 'https://electrum.org'],
            Commands._setconfig_normalize_value('url_rewrite', "['file:///var/www/','https://electrum.org']"))
        self.assertEqual(['file:///var/www/', 'https://electrum.org'],
            Commands._setconfig_normalize_value('url_rewrite', '["file:///var/www/","https://electrum.org"]'))

    def test_setconfig_auth(self):
        self.assertEqual("7777", Commands._setconfig_normalize_value('rpcuser', "7777"))
        self.assertEqual("7777", Commands._setconfig_normalize_value('rpcuser', '7777'))
        self.assertEqual("7777", Commands._setconfig_normalize_value('rpcpassword', '7777'))
        self.assertEqual("2asd", Commands._setconfig_normalize_value('rpcpassword', '2asd'))
        self.assertEqual("['file:///var/www/','https://electrum.org']",
            Commands._setconfig_normalize_value('rpcpassword', "['file:///var/www/','https://electrum.org']"))

    def test_eval_bool(self):
        self.assertFalse(eval_bool("False"))
        self.assertFalse(eval_bool("false"))
        self.assertFalse(eval_bool("0"))
        self.assertTrue(eval_bool("True"))
        self.assertTrue(eval_bool("true"))
        self.assertTrue(eval_bool("1"))

    def test_convert_xkey(self):
        cmds = Commands(config=self.config)
        xpubs = {
            ("xpub6CCWFbvCbqF92kGwm9nV7t7RvVoQUKaq5USMdyVP6jvv1NgN52KAX6NNYCeE8Ca7JQC4K5tZcnQrubQcjJ6iixfPs4pwAQJAQgTt6hBjg11", "standard"),
        }
        for xkey1, xtype1 in xpubs:
            for xkey2, xtype2 in xpubs:
                self.assertEqual(xkey2, cmds._run('convert_xkey', (xkey1, xtype2)))

        xprvs = {
            ("xprv9yD9r6PJmTgqpGCUf8FUkkAhNTxv4rryiFWkqb5mYQPw8aMDXUzuyJ3tgv5vUqYkdK1E6Q5jKxPss4HkMBYV4q8AfG8t7rxgyS4xQX4ndAm", "standard"),
        }
        for xkey1, xtype1 in xprvs:
            for xkey2, xtype2 in xprvs:
                self.assertEqual(xkey2, cmds._run('convert_xkey', (xkey1, xtype2)))

    @mock.patch.object(wallet.Abstract_Wallet, 'save_db')
    def test_encrypt_decrypt(self, mock_save_db):
        wallet = restore_wallet_from_text('p2pkh:L4rYY5QpfN6wJEF4SEKDpcGhTPnCe9zcGs6hiSnhpprZqVywFifN',
                                          path='if_this_exists_mocking_failed_648151893',
                                          config=self.config)['wallet']
        cmds = Commands(config=self.config)
        cleartext = "asdasd this is the message"
        pubkey = "021f110909ded653828a254515b58498a6bafc96799fb0851554463ed44ca7d9da"
        ciphertext = cmds._run('encrypt', (pubkey, cleartext))
        self.assertEqual(cleartext, cmds._run('decrypt', (pubkey, ciphertext), wallet=wallet))

    @mock.patch.object(wallet.Abstract_Wallet, 'save_db')
    def test_export_private_key_imported(self, mock_save_db):
        wallet = restore_wallet_from_text('p2pkh:L2tCtZNQ2kHhNPMYnnxGaqzBfP3q9qkF8GLGAaqt83DYQiHm4cH6 p2pkh:KziELqRDg4EyiUE2uTc4FdKV1i9oPb7oaoXqmn3y1VJD4hNnJ2nG',
                                          path='if_this_exists_mocking_failed_648151893',
                                          config=self.config)['wallet']
        cmds = Commands(config=self.config)
        # single address tests
        with self.assertRaises(Exception):
            cmds._run('getprivatekeys', ("asdasd",), wallet=wallet)  # invalid addr, though might raise "not in wallet"
        with self.assertRaises(Exception):
            cmds._run('getprivatekeys', ("t1LQ4AarpUGURKZ2gcBjmgFVobEdBJQY49R",), wallet=wallet)  # not in wallet
        self.assertEqual("p2pkh:KziELqRDg4EyiUE2uTc4FdKV1i9oPb7oaoXqmn3y1VJD4hNnJ2nG",
                         cmds._run('getprivatekeys', ("t1KtqVs7jkuRqd7CTh1ZeE4QS61Br7vW4C8",), wallet=wallet))
        # list of addresses tests
        with self.assertRaises(Exception):
            cmds._run('getprivatekeys', (['t1UaodrrMGJS83dpqyFPcX4bP7SB2zhiWKX', 'asd'],), wallet=wallet)
        self.assertEqual(['p2pkh:L2tCtZNQ2kHhNPMYnnxGaqzBfP3q9qkF8GLGAaqt83DYQiHm4cH6', 'p2pkh:KziELqRDg4EyiUE2uTc4FdKV1i9oPb7oaoXqmn3y1VJD4hNnJ2nG'],
                         cmds._run('getprivatekeys', (['t1UaodrrMGJS83dpqyFPcX4bP7SB2zhiWKX', 't1KtqVs7jkuRqd7CTh1ZeE4QS61Br7vW4C8'],), wallet=wallet))

    @mock.patch.object(wallet.Abstract_Wallet, 'save_db')
    def test_export_private_key_deterministic(self, mock_save_db):
        wallet = restore_wallet_from_text('hint shock chair puzzle shock traffic drastic note dinosaur mention suggest sweet',
                                          gap_limit=2,
                                          path='if_this_exists_mocking_failed_648151893',
                                          config=self.config)['wallet']
        cmds = Commands(config=self.config)
        # single address tests
        with self.assertRaises(Exception):
            cmds._run('getprivatekeys', ("asdasd",), wallet=wallet)  # invalid addr, though might raise "not in wallet"
        with self.assertRaises(Exception):
            cmds._run('getprivatekeys', ("t1LQ4AarpUGURKZ2gcBjmgFVobEdBJQY49R",), wallet=wallet)  # not in wallet
        self.assertEqual("p2pkh:Kz1ZnW7x6jgdJnk2KuwDpccQu1yNsi5LGcyySMS1vpgCu2b75HBn",
                         cmds._run('getprivatekeys', ("t1dx4B4At925cNcTS29WHfePS6uRAVrevv9",), wallet=wallet))
        # list of addresses tests
        with self.assertRaises(Exception):
            cmds._run('getprivatekeys', (['t1dx4B4At925cNcTS29WHfePS6uRAVrevv9', 'asd'],), wallet=wallet)
        self.assertEqual(['p2pkh:Kz1ZnW7x6jgdJnk2KuwDpccQu1yNsi5LGcyySMS1vpgCu2b75HBn', 'p2pkh:L2pttW6uTtoLcbRYbJr5wR36Up3EGLeEJBLUnggs5HXDUQ5ti2kF'],
                         cmds._run('getprivatekeys', (['t1dx4B4At925cNcTS29WHfePS6uRAVrevv9', 't1WREVU9xPr2g6htNsxGhLZgYSBAF9grmpU'],), wallet=wallet))


class TestCommandsTestnet(TestCaseForTestnet):

    def setUp(self):
        super().setUp()
        self.asyncio_loop, self._stop_loop, self._loop_thread = create_and_start_event_loop()
        self.config = SimpleConfig({'electrum_path': self.electrum_path})

    def tearDown(self):
        super().tearDown()
        self.asyncio_loop.call_soon_threadsafe(self._stop_loop.set_result, 1)
        self._loop_thread.join(timeout=1)

    def test_convert_xkey(self):
        cmds = Commands(config=self.config)
        xpubs = {
            ("tpubD8p5qNfjczgTGbh9qgNxsbFgyhv8GgfVkmp3L88qtRm5ibUYiDVCrn6WYfnGey5XVVw6Bc5QNQUZW5B4jFQsHjmaenvkFUgWtKtgj5AdPm9", "standard"),
        }
        for xkey1, xtype1 in xpubs:
            for xkey2, xtype2 in xpubs:
                self.assertEqual(xkey2, cmds._run('convert_xkey', (xkey1, xtype2)))

        xprvs = {
            ("tprv8c83gxdVUcznP8fMx2iNUBbaQgQC7MUbBUDG3c6YU9xgt7Dn5pfcgHUeNZTAvuYmNgVHjyTzYzGWwJr7GvKCm2FkPaaJipyipbfJeB3tdPW", "standard"),
        }
        for xkey1, xtype1 in xprvs:
            for xkey2, xtype2 in xprvs:
                self.assertEqual(xkey2, cmds._run('convert_xkey', (xkey1, xtype2)))

    def test_serialize(self):
        cmds = Commands(config=self.config)
        jsontx = {
            "version": 2,
            "inputs": [
                {
                    "prevout_hash": "9d221a69ca3997cbeaf5624d723e7dc5f829b1023078c177d37bdae95f37c539",
                    "prevout_n": 1,
                    "value_sats": 1000000,
                    "privkey": "p2pkh:cVDXzzQg6RoCTfiKpe8MBvmm5d5cJc6JLuFApsFDKwWa6F5TVHpD"
                }
            ],
            "outputs": [
                {
                    "address": "tmJktQA6NJ5zSGS2o27jBzzYppiGjFR1HRp",
                    "value_sats": 990000
                }
            ]
        }
        self.assertEqual("020000000139c5375fe9da7bd377c1783002b129f8c57d3e724d62f5eacb9739ca691a229d010000006a4730440220724a67810148fdc9474a71fafd116065d918c494dbabd4ad979a597045e9291c0220728fc15a0422cdb2624d6642fdd2e3c817131c5563309c8a6ac7a02846a082000121021f110909ded653828a254515b58498a6bafc96799fb0851554463ed44ca7d9dafeffffff01301b0f00000000001976a9146333e61a83cf112553c2f93629dbc9bba70b594f88ac00000000",
                         cmds._run('serialize', (jsontx,)))

    def test_serialize_custom_nsequence(self):
        cmds = Commands(config=self.config)
        jsontx = {
            "version": 2,
            "inputs": [
                {
                    "prevout_hash": "9d221a69ca3997cbeaf5624d723e7dc5f829b1023078c177d37bdae95f37c539",
                    "prevout_n": 1,
                    "value_sats": 1000000,
                    "privkey": "p2pkh:cVDXzzQg6RoCTfiKpe8MBvmm5d5cJc6JLuFApsFDKwWa6F5TVHpD",
                    "nsequence": 0xfffffffd
                }
            ],
            "outputs": [
                {
                    "address": "tmJktQA6NJ5zSGS2o27jBzzYppiGjFR1HRp",
                    "value_sats": 990000
                }
            ]
        }
        print(cmds._run('serialize', (jsontx,)))
        self.assertEqual("020000000139c5375fe9da7bd377c1783002b129f8c57d3e724d62f5eacb9739ca691a229d010000006a4730440220100ca9083e11fb3adfc201591c8de7d6c8f6da70cddf090416ed4e7d54a1277702200c86304c89a187075d4992eb4741794f28aef08c1d025a009fb52d9ada8039860121021f110909ded653828a254515b58498a6bafc96799fb0851554463ed44ca7d9dafdffffff01301b0f00000000001976a9146333e61a83cf112553c2f93629dbc9bba70b594f88ac00000000",
                         cmds._run('serialize', (jsontx,)))

    @mock.patch.object(wallet.Abstract_Wallet, 'save_db')
    def test_getprivatekeyforpath(self, mock_save_db):
        wallet = restore_wallet_from_text('hint shock chair puzzle shock traffic drastic note dinosaur mention suggest sweet',
                                          gap_limit=2,
                                          path='if_this_exists_mocking_failed_648151893',
                                          config=self.config)['wallet']
        cmds = Commands(config=self.config)
        self.assertEqual("p2pkh:cRVRdGfHrP9zb3cNTT1HGoG9JPcZfvjBMqUa2vTDMGDnKG1dNu24",
                         cmds._run('getprivatekeyforpath', ([0, 10000],), wallet=wallet))
        self.assertEqual("p2pkh:cRVRdGfHrP9zb3cNTT1HGoG9JPcZfvjBMqUa2vTDMGDnKG1dNu24",
                         cmds._run('getprivatekeyforpath', ("m/0/10000",), wallet=wallet))
        self.assertEqual("p2pkh:cS2exaULytoQ9CR89QHJDMg82NWKZ6f8rFboU7LGbHhdUMXxpPcd",
                         cmds._run('getprivatekeyforpath', ("m/5h/100000/88h/7",), wallet=wallet))

    @mock.patch.object(wallet.Abstract_Wallet, 'save_db')
    def test_signtransaction_without_wallet(self, mock_save_db):
        dummy_wallet = restore_wallet_from_text(
            'tmMNULUhE7uCJk8W6TJBCztSEeWGb8FFXLW',  # random testnet address
            gap_limit=2, path='if_this_exists_mocking_failed_648151893', config=self.config)['wallet']
        cmds = Commands(config=self.config)
        unsigned_tx = "cHNidP8BAFUCAAAAAfYPG8xEZIPSCFUQvT9hKSebChcHfRf44VBKdvCv+BvUAQAAAAD+////AVtGSgAAAAAAGXapFHbdRv3NIGILeiru0ElFh/yu1oXmiKxePwcAAAEA/SUBAgAAAAF895Ja488aAx4I7yq55Jxlr50rK3fkjjIx3Uxsgh7Z8wAAAABqRzBEAiBAE2MpeZYzp5QC2J7V9/KfvF7uQk/XcUs8YI9K+12zBAIgex7/mvNPvdj91u7WFnCMSJZAHxMW1XGvPD815CbeJ3wBIQK8Z9v+zCc0HugaBAKfsufI4SgHicvnhb2rbgZz8ceFuf7///8EQJwAAAAAAAAZdqkU+InI3CUUVo7OLrKa7Q7hZ6qArceIrHtHSgAAAAAAGXapFMXi0i9hMWlau5GQFeiPwlJxs4dQiKzklpgAAAAAABl2qRQjqj1H4J1g4HSr2IvCdVOedvNkQIis5JaYAAAAAAAZdqkU+gvqRTG5zwueDUbg7AZ1AQmAF9aIrJ01BwAiBgK8Z9v+zCc0HugaBAKfsufI4SgHicvnhb2rbgZz8ceFuQzZ3FryAAAAAAAAAAAAIgIDJgOS9iOn/pO/96NpC3pK5xamEiGEQs3wIF/8r9G1G+MM2dxa8gAAAAAIAAAAAA=="
        assert not tx_from_any(unsigned_tx).is_complete()
        privkey = "cVigSP6aKjWJVX9Gp1fGMLJyCbuxYWaMBVQyjUt5mL17WhMH53e6"
        tx_str = cmds._run('signtransaction', (), tx=unsigned_tx, privkey=privkey, wallet=dummy_wallet)
        self.assertEqual(tx_str,
                         "0200000001f60f1bcc446483d2085510bd3f6129279b0a17077d17f8e1504a76f0aff81bd4010000006a473044022040ea78e690d2a323daadc19831b3d1294e2a28d96c48481677c9786d9a1be3ac0220672ce6745e5de73f61cefb0f2f3fac5ce5aa9b9728fd28efb55e0660f92cc3d9012102bc67dbfecc27341ee81a04029fb2e7c8e1280789cbe785bdab6e0673f1c785b9feffffff015b464a00000000001976a91476dd46fdcd20620b7a2aeed0494587fcaed685e688ac5e3f0700")
        assert  tx_from_any(tx_str).is_complete()
