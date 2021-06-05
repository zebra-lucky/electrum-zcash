import time
from typing import TYPE_CHECKING, List, Optional, Union, Dict, Any
from decimal import Decimal

import attr

from .json_db import StoredObject
from .i18n import _
from .util import age
from . import constants
from .bitcoin import COIN, TOTAL_COIN_SUPPLY_LIMIT_IN_BTC
from .transaction import PartialTxOutput

if TYPE_CHECKING:
    from .paymentrequest import PaymentRequest

# convention: 'invoices' = outgoing , 'request' = incoming

# types of payment requests
PR_TYPE_ONCHAIN = 0

# status of payment requests
PR_UNPAID   = 0
PR_EXPIRED  = 1
PR_UNKNOWN  = 2     # sent but not propagated
PR_PAID     = 3     # send and propagated
PR_INFLIGHT = 4     # unconfirmed
PR_FAILED   = 5
PR_ROUTING  = 6
PR_UNCONFIRMED = 7

pr_color = {
    PR_UNPAID:   (.7, .7, .7, 1),
    PR_PAID:     (.2, .9, .2, 1),
    PR_UNKNOWN:  (.7, .7, .7, 1),
    PR_EXPIRED:  (.9, .2, .2, 1),
    PR_INFLIGHT: (.9, .6, .3, 1),
    PR_FAILED:   (.9, .2, .2, 1),
    PR_ROUTING: (.9, .6, .3, 1),
    PR_UNCONFIRMED: (.9, .6, .3, 1),
}

pr_tooltips = {
    PR_UNPAID:_('Unpaid'),
    PR_PAID:_('Paid'),
    PR_UNKNOWN:_('Unknown'),
    PR_EXPIRED:_('Expired'),
    PR_INFLIGHT:_('In progress'),
    PR_FAILED:_('Failed'),
    PR_ROUTING: _('Computing route...'),
    PR_UNCONFIRMED: _('Unconfirmed'),
}

PR_DEFAULT_EXPIRATION_WHEN_CREATING = 24*60*60  # 1 day
pr_expiration_values = {
    0: _('Never'),
    10*60: _('10 minutes'),
    60*60: _('1 hour'),
    24*60*60: _('1 day'),
    7*24*60*60: _('1 week'),
}
assert PR_DEFAULT_EXPIRATION_WHEN_CREATING in pr_expiration_values


def _decode_outputs(outputs) -> List[PartialTxOutput]:
    ret = []
    for output in outputs:
        if not isinstance(output, PartialTxOutput):
            output = PartialTxOutput.from_legacy_tuple(*output)
        ret.append(output)
    return ret


@attr.s
class Invoice(StoredObject):
    type = attr.ib(type=int, kw_only=True)

    message: str
    exp: int
    time: int

    def get_status_str(self, status):
        status_str = pr_tooltips[status]
        if status == PR_UNPAID:
            if self.exp > 0:
                expiration = self.exp + self.time
                status_str = _('Expires') + ' ' + age(expiration, include_seconds=True)
        return status_str

    def get_amount_sat(self) -> Union[int, Decimal, str, None]:
        """Returns a decimal satoshi amount, or '!' or None."""
        raise NotImplementedError()

    @classmethod
    def from_json(cls, x: dict) -> 'Invoice':
        # note: these raise if x has extra fields
        if x.get('type') == PR_TYPE_ONCHAIN:
            return OnchainInvoice(**x)
        else:
            raise Exception('Unknown invoice type')


@attr.s
class OnchainInvoice(Invoice):
    message = attr.ib(type=str, kw_only=True)
    amount_sat = attr.ib(kw_only=True)  # type: Union[int, str]  # in satoshis. can be '!'
    exp = attr.ib(type=int, kw_only=True, validator=attr.validators.instance_of(int))
    time = attr.ib(type=int, kw_only=True, validator=attr.validators.instance_of(int))
    id = attr.ib(type=str, kw_only=True)
    outputs = attr.ib(kw_only=True, converter=_decode_outputs)  # type: List[PartialTxOutput]
    bip70 = attr.ib(type=str, kw_only=True)  # type: Optional[str]
    requestor = attr.ib(type=str, kw_only=True)  # type: Optional[str]
    height = attr.ib(type=int, kw_only=True, validator=attr.validators.instance_of(int))

    def get_address(self) -> str:
        """returns the first address, to be displayed in GUI"""
        return self.outputs[0].address

    def get_amount_sat(self) -> Union[int, str]:
        return self.amount_sat or 0

    @amount_sat.validator
    def _validate_amount(self, attribute, value):
        if isinstance(value, int):
            if not (0 <= value <= TOTAL_COIN_SUPPLY_LIMIT_IN_BTC * COIN):
                raise ValueError(f"amount is out-of-bounds: {value!r} sat")
        elif isinstance(value, str):
            if value != "!":
                raise ValueError(f"unexpected amount: {value!r}")
        else:
            raise ValueError(f"unexpected amount: {value!r}")

    @classmethod
    def from_bip70_payreq(cls, pr: 'PaymentRequest', height:int) -> 'OnchainInvoice':
        return OnchainInvoice(
            type=PR_TYPE_ONCHAIN,
            amount_sat=pr.get_amount(),
            outputs=pr.get_outputs(),
            message=pr.get_memo(),
            id=pr.get_id(),
            time=pr.get_time(),
            exp=pr.get_expiration_date() - pr.get_time(),
            bip70=pr.raw.hex(),
            requestor=pr.get_requestor(),
            height=height,
        )
