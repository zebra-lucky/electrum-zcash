#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Search and replaces Dash addresses and
   private keys in WIF to Zcash variant"""

import click
import imp
import re

imp.load_module('electrum_zcash', *imp.find_module('../../electrum_zcash'))

from electrum_zcash import constants
from electrum_zcash.bitcoin import (hash160_to_b58_address, serialize_privkey,
                                    DecodeBase58Check, WIF_SCRIPT_TYPES_INV,
                                    WIF_SCRIPT_TYPES)
from electrum_zcash.util import to_bytes


ADDR_PATTERN = re.compile(
    '([123456789ABCDEFGHJKLMNPQRSTUVWXYZ'
    'abcdefghijkmnopqrstuvwxyz]{20,80})')


def dash_b58_address_to_hash160(addr):
    addr = to_bytes(addr, 'ascii')
    _bytes = DecodeBase58Check(addr)
    if len(_bytes) != 21:
        raise Exception(f'expected 21 payload bytes in base58 address.'
                        f' got: {len(_bytes)}')
    return _bytes[0], _bytes[1:21]


def deserialize_dash_privkey(key, wif_prefix):
    try:
        vch = DecodeBase58Check(key)
    except Exception as e:
        return None, None, None

    prefix_value = vch[0] - wif_prefix
    try:
        txin_type = WIF_SCRIPT_TYPES_INV[prefix_value]
    except KeyError as e:
        return None, None, None

    if len(vch) not in [33, 34]:
        return None, None, None

    compressed = len(vch) == 34
    #return txin_type, vch[1:33] if compressed else vch[1:32], compressed
    return txin_type, vch[1:33], compressed


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('-i', '--input-file', required=True,
              help='Input file')
@click.option('-n', '--dry-run', is_flag=True,
              help='Only show what will be changed')
@click.option('-o', '--output-file',
              help='Output file')
@click.option('-p', '--inplace', is_flag=True,
              help='Replace data inplace')
@click.option('-t', '--testnet', is_flag=True,
              help='Use testnet network constants')
def main(**kwargs):
    input_file = kwargs.pop('input_file')
    output_file = kwargs.pop('output_file', None)
    inplace = kwargs.pop('inplace', False)
    dry_run = kwargs.pop('dry_run', False)
    testnet = kwargs.pop('testnet', False)

    if testnet:
        constants.set_testnet()
        DASH_ADDRTYPE_P2PKH = 140
        DASH_ADDRTYPE_P2SH = 19
        DASH_WIF_PREFIX = 239
    else:
        DASH_ADDRTYPE_P2PKH = 76
        DASH_ADDRTYPE_P2SH = 16
        DASH_WIF_PREFIX = 204

    net = constants.net

    if inplace:
        output_file = input_file

    olines = []
    total_sub = 0
    for ln, l in enumerate(open(input_file, 'r').read().splitlines()):
        pos = 0
        ol = ''

        while pos < len(l):
            m = ADDR_PATTERN.search(l, pos)
            if not m:
                ol += l[pos:]
                break

            ol += l[pos:m.start()]
            val = m.group()

            try:
                addrtype, h = dash_b58_address_to_hash160(val)
            except:
                h = None

            if h and addrtype == DASH_ADDRTYPE_P2PKH:
                new_val = hash160_to_b58_address(h, net.ADDRTYPE_P2PKH)
                total_sub +=1
            elif h and addrtype == DASH_ADDRTYPE_P2SH:
                new_val = hash160_to_b58_address(h, net.ADDRTYPE_P2SH)
                total_sub +=1
            else:
                new_val = None



            if not new_val:
                try:
                    txin_type, privkey, compressed = \
                        deserialize_dash_privkey(val, DASH_WIF_PREFIX)
                except Exception as e:
                    privkey = None

                if privkey:
                    new_val = serialize_privkey(privkey, compressed, txin_type,
                                                internal_use=True)

            if dry_run and new_val:
                print('line %s, col %s: %s => %s' % (
                    ln, m.start(), val, new_val
                ))

            ol += new_val if new_val else val
            pos = m.end()

        olines.append(ol)

    out = '\n'.join(olines)
    if not output_file:
        print(out)
    elif not dry_run:
        with open(output_file, 'w') as wfd:
            wfd.write('%s\n' % out)
    else:
        print('Total sub count:', total_sub)


if __name__ == '__main__':
    main()
